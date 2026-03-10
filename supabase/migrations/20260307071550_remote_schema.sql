


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE OR REPLACE FUNCTION "public"."invoice_topic"("p_user" "uuid") RETURNS "text"
    LANGUAGE "sql" STABLE
    AS $$
  SELECT 'user:' || p_user::text || ':invoices';
$$;


ALTER FUNCTION "public"."invoice_topic"("p_user" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."invoices_broadcast_trigger"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  -- Broadcast the change to the user's private topic
  PERFORM realtime.broadcast_changes(
    invoice_topic(COALESCE(NEW.user_id, OLD.user_id)),
    TG_OP,
    TG_OP,
    TG_TABLE_NAME,
    TG_TABLE_SCHEMA,
    NEW,
    OLD
  );
  RETURN COALESCE(NEW, OLD);
END;
$$;


ALTER FUNCTION "public"."invoices_broadcast_trigger"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."rls_auto_enable"() RETURNS "event_trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'pg_catalog'
    AS $$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN
    SELECT *
    FROM pg_event_trigger_ddl_commands()
    WHERE command_tag IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
      AND object_type IN ('table','partitioned table')
  LOOP
     IF cmd.schema_name IS NOT NULL AND cmd.schema_name IN ('public') AND cmd.schema_name NOT IN ('pg_catalog','information_schema') AND cmd.schema_name NOT LIKE 'pg_toast%' AND cmd.schema_name NOT LIKE 'pg_temp%' THEN
      BEGIN
        EXECUTE format('alter table if exists %s enable row level security', cmd.object_identity);
        RAISE LOG 'rls_auto_enable: enabled RLS on %', cmd.object_identity;
      EXCEPTION
        WHEN OTHERS THEN
          RAISE LOG 'rls_auto_enable: failed to enable RLS on %', cmd.object_identity;
      END;
     ELSE
        RAISE LOG 'rls_auto_enable: skip % (either system schema or not in enforced list: %.)', cmd.object_identity, cmd.schema_name;
     END IF;
  END LOOP;
END;
$$;


ALTER FUNCTION "public"."rls_auto_enable"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."set_updated_at"() OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."api_keys" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "label" "text" NOT NULL,
    "hint" "text" NOT NULL,
    "hashed_key" "text" NOT NULL,
    "environment" "text" DEFAULT 'live'::"text" NOT NULL,
    "revoked" boolean DEFAULT false NOT NULL,
    "revoked_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "last_used_at" timestamp with time zone,
    CONSTRAINT "api_keys_environment_check" CHECK (("environment" = ANY (ARRAY['live'::"text", 'test'::"text"])))
);


ALTER TABLE "public"."api_keys" OWNER TO "postgres";


COMMENT ON TABLE "public"."api_keys" IS 'API keys for programmatic access. Raw key shown once on creation.';



COMMENT ON COLUMN "public"."api_keys"."hint" IS 'First 20 characters of the key for display purposes only.';



COMMENT ON COLUMN "public"."api_keys"."hashed_key" IS 'bcrypt hash (work factor 12) of the full raw key. Used for constant-time verification on every request.';



COMMENT ON COLUMN "public"."api_keys"."revoked" IS 'Soft delete — revoked keys are retained for audit. Set true to instantly block the key.';



COMMENT ON COLUMN "public"."api_keys"."last_used_at" IS 'Updated on every successful authentication. Useful for identifying stale or compromised keys.';



CREATE OR REPLACE VIEW "public"."active_api_keys" WITH ("security_invoker"='on') AS
 SELECT "id",
    "user_id",
    "label",
    "hint",
    "hashed_key",
    "environment",
    "revoked",
    "revoked_at",
    "created_at",
    "last_used_at"
   FROM "public"."api_keys"
  WHERE ("revoked" = false);


ALTER VIEW "public"."active_api_keys" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."invoices" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "contract_ref" "text" NOT NULL,
    "status" "text" DEFAULT 'draft'::"text" NOT NULL,
    "currency" "text" DEFAULT 'AUD'::"text" NOT NULL,
    "total_amount" numeric(12,2) DEFAULT 0 NOT NULL,
    "tax_amount" numeric(12,2) DEFAULT 0 NOT NULL,
    "due_amount" numeric(12,2) DEFAULT 0 NOT NULL,
    "customer_data" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "s3_key" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "exported_at" timestamp with time zone,
    CONSTRAINT "invoices_status_check" CHECK (("status" = ANY (ARRAY['draft'::"text", 'finalised'::"text", 'exported'::"text", 'paid'::"text", 'cancelled'::"text"])))
);


ALTER TABLE "public"."invoices" OWNER TO "postgres";


COMMENT ON TABLE "public"."invoices" IS 'Invoice records. XML stored in S3; table holds metadata and financial summary.';



COMMENT ON COLUMN "public"."invoices"."total_amount" IS 'Gross total calculated from order document and contract rates.';



COMMENT ON COLUMN "public"."invoices"."due_amount" IS 'Remaining balance. Equals total_amount - any credit applied. No credits table — updated directly.';



COMMENT ON COLUMN "public"."invoices"."customer_data" IS 'JSONB of customer info.';



COMMENT ON COLUMN "public"."invoices"."s3_key" IS 'Full S3 object key for the UBL XML file. Null until the invoice is exported.';



CREATE OR REPLACE VIEW "public"."invoice_summaries" WITH ("security_invoker"='on') AS
 SELECT "id",
    "user_id",
    "contract_ref",
    "status",
    "currency",
    "total_amount",
    "tax_amount",
    "due_amount",
    ("customer_data" ->> 'name'::"text") AS "customer_name",
    ("customer_data" ->> 'email'::"text") AS "customer_email",
    ("s3_key" IS NOT NULL) AS "has_export",
    "created_at",
    "updated_at",
    "exported_at"
   FROM "public"."invoices";


ALTER VIEW "public"."invoice_summaries" OWNER TO "postgres";


COMMENT ON VIEW "public"."invoice_summaries" IS 'Flattened invoice list for GET /v1/invoices.';



CREATE TABLE IF NOT EXISTS "public"."refresh_tokens" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "token_hash" "text" NOT NULL,
    "expires_at" timestamp with time zone DEFAULT ("now"() + '24:00:00'::interval) NOT NULL,
    "revoked" boolean DEFAULT false NOT NULL,
    "revoked_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "last_used_at" timestamp with time zone
);


ALTER TABLE "public"."refresh_tokens" OWNER TO "postgres";


COMMENT ON TABLE "public"."refresh_tokens" IS 'Server-side refresh token records for browser JWT sessions.';



COMMENT ON COLUMN "public"."refresh_tokens"."token_hash" IS 'SHA-256 hash of the raw token. Raw only in httpOnly cookie.';



COMMENT ON COLUMN "public"."refresh_tokens"."revoked" IS 'Set true on logout or suspicious activity. Checked on every refresh attempt.';



CREATE TABLE IF NOT EXISTS "public"."users" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "email" "text" NOT NULL,
    "password_hash" "text" NOT NULL,
    "verified" boolean DEFAULT false NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."users" OWNER TO "postgres";


COMMENT ON TABLE "public"."users" IS 'Registered UNSW student accounts.';



COMMENT ON COLUMN "public"."users"."password_hash" IS 'bcrypt hash of the user password. Raw password is never stored.';



COMMENT ON COLUMN "public"."users"."verified" IS 'False until the user clicks the email verification link.';



CREATE TABLE IF NOT EXISTS "public"."verification_tokens" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "token" "text" NOT NULL,
    "purpose" "text" NOT NULL,
    "expires_at" timestamp with time zone DEFAULT ("now"() + '00:30:00'::interval) NOT NULL,
    "used_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "verification_tokens_purpose_check" CHECK (("purpose" = ANY (ARRAY['email_verify'::"text", 'password_reset'::"text"])))
);


ALTER TABLE "public"."verification_tokens" OWNER TO "postgres";


COMMENT ON TABLE "public"."verification_tokens" IS 'Single-use tokens for email verification and password reset.';



COMMENT ON COLUMN "public"."verification_tokens"."token" IS 'Random token — secrets.token_urlsafe(32). Never predictable.';



COMMENT ON COLUMN "public"."verification_tokens"."used_at" IS 'Set when consumed. Non-null means token no longer valid.';



ALTER TABLE ONLY "public"."api_keys"
    ADD CONSTRAINT "api_keys_hashed_key_key" UNIQUE ("hashed_key");



ALTER TABLE ONLY "public"."api_keys"
    ADD CONSTRAINT "api_keys_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."invoices"
    ADD CONSTRAINT "invoices_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."refresh_tokens"
    ADD CONSTRAINT "refresh_tokens_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."refresh_tokens"
    ADD CONSTRAINT "refresh_tokens_token_hash_key" UNIQUE ("token_hash");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_email_key" UNIQUE ("email");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."verification_tokens"
    ADD CONSTRAINT "verification_tokens_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."verification_tokens"
    ADD CONSTRAINT "verification_tokens_token_key" UNIQUE ("token");



CREATE INDEX "idx_api_keys_hashed_key" ON "public"."api_keys" USING "btree" ("hashed_key");



CREATE INDEX "idx_api_keys_hint" ON "public"."api_keys" USING "btree" ("hint");



CREATE INDEX "idx_api_keys_user_id" ON "public"."api_keys" USING "btree" ("user_id");



CREATE INDEX "idx_invoices_active" ON "public"."invoices" USING "btree" ("user_id", "created_at" DESC) WHERE ("status" <> 'cancelled'::"text");



CREATE INDEX "idx_invoices_created_at" ON "public"."invoices" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_invoices_status" ON "public"."invoices" USING "btree" ("status");



CREATE INDEX "idx_invoices_user_id" ON "public"."invoices" USING "btree" ("user_id");



CREATE INDEX "idx_refresh_tokens_token_hash" ON "public"."refresh_tokens" USING "btree" ("token_hash");



CREATE INDEX "idx_refresh_tokens_user_id" ON "public"."refresh_tokens" USING "btree" ("user_id");



CREATE INDEX "idx_users_email" ON "public"."users" USING "btree" ("email");



CREATE INDEX "idx_verification_tokens_token" ON "public"."verification_tokens" USING "btree" ("token");



CREATE INDEX "idx_verification_tokens_user_id" ON "public"."verification_tokens" USING "btree" ("user_id");



CREATE OR REPLACE TRIGGER "trg_invoices_broadcast" AFTER INSERT OR DELETE OR UPDATE ON "public"."invoices" FOR EACH ROW EXECUTE FUNCTION "public"."invoices_broadcast_trigger"();



CREATE OR REPLACE TRIGGER "trg_invoices_updated_at" BEFORE UPDATE ON "public"."invoices" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();



CREATE OR REPLACE TRIGGER "trg_users_updated_at" BEFORE UPDATE ON "public"."users" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();



ALTER TABLE ONLY "public"."api_keys"
    ADD CONSTRAINT "api_keys_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."invoices"
    ADD CONSTRAINT "invoices_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."refresh_tokens"
    ADD CONSTRAINT "refresh_tokens_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."verification_tokens"
    ADD CONSTRAINT "verification_tokens_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE "public"."api_keys" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "api_keys_delete_owner" ON "public"."api_keys" FOR DELETE TO "authenticated" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "api_keys_insert_owner" ON "public"."api_keys" FOR INSERT TO "authenticated" WITH CHECK (("user_id" = "auth"."uid"()));



CREATE POLICY "api_keys_owner" ON "public"."api_keys" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "api_keys_select_owner" ON "public"."api_keys" FOR SELECT TO "authenticated" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "api_keys_update_owner" ON "public"."api_keys" FOR UPDATE TO "authenticated" USING (("user_id" = "auth"."uid"())) WITH CHECK (("user_id" = "auth"."uid"()));



ALTER TABLE "public"."invoices" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "invoices_delete_owner" ON "public"."invoices" FOR DELETE TO "authenticated" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "invoices_insert_owner" ON "public"."invoices" FOR INSERT TO "authenticated" WITH CHECK (("user_id" = "auth"."uid"()));



CREATE POLICY "invoices_owner" ON "public"."invoices" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "invoices_select_owner" ON "public"."invoices" FOR SELECT TO "authenticated" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "invoices_update_owner" ON "public"."invoices" FOR UPDATE TO "authenticated" USING (("user_id" = "auth"."uid"())) WITH CHECK (("user_id" = "auth"."uid"()));



ALTER TABLE "public"."refresh_tokens" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "refresh_tokens_insert_for_self" ON "public"."refresh_tokens" FOR INSERT TO "authenticated" WITH CHECK (("user_id" = "auth"."uid"()));



CREATE POLICY "refresh_tokens_owner" ON "public"."refresh_tokens" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "refresh_tokens_select_owner" ON "public"."refresh_tokens" FOR SELECT TO "authenticated" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "refresh_tokens_update_owner" ON "public"."refresh_tokens" FOR UPDATE TO "authenticated" USING (("user_id" = "auth"."uid"())) WITH CHECK (("user_id" = "auth"."uid"()));



ALTER TABLE "public"."users" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "users_select_self" ON "public"."users" FOR SELECT TO "authenticated" USING (("id" = "auth"."uid"()));



CREATE POLICY "users_self" ON "public"."users" USING (("id" = "auth"."uid"()));



CREATE POLICY "users_update_self" ON "public"."users" FOR UPDATE TO "authenticated" USING (("id" = "auth"."uid"())) WITH CHECK (("id" = "auth"."uid"()));



ALTER TABLE "public"."verification_tokens" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "verification_tokens_insert_for_self" ON "public"."verification_tokens" FOR INSERT TO "authenticated" WITH CHECK (("user_id" = "auth"."uid"()));



CREATE POLICY "verification_tokens_owner" ON "public"."verification_tokens" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "verification_tokens_select_owner" ON "public"."verification_tokens" FOR SELECT TO "authenticated" USING (("user_id" = "auth"."uid"()));



GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";

























































































































































REVOKE ALL ON FUNCTION "public"."invoice_topic"("p_user" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."invoice_topic"("p_user" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."invoice_topic"("p_user" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."invoice_topic"("p_user" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "public"."invoices_broadcast_trigger"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."invoices_broadcast_trigger"() TO "anon";
GRANT ALL ON FUNCTION "public"."invoices_broadcast_trigger"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."invoices_broadcast_trigger"() TO "service_role";



GRANT ALL ON FUNCTION "public"."rls_auto_enable"() TO "anon";
GRANT ALL ON FUNCTION "public"."rls_auto_enable"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."rls_auto_enable"() TO "service_role";



GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "service_role";


















GRANT ALL ON TABLE "public"."api_keys" TO "anon";
GRANT ALL ON TABLE "public"."api_keys" TO "authenticated";
GRANT ALL ON TABLE "public"."api_keys" TO "service_role";



GRANT ALL ON TABLE "public"."active_api_keys" TO "anon";
GRANT ALL ON TABLE "public"."active_api_keys" TO "authenticated";
GRANT ALL ON TABLE "public"."active_api_keys" TO "service_role";



GRANT ALL ON TABLE "public"."invoices" TO "anon";
GRANT ALL ON TABLE "public"."invoices" TO "authenticated";
GRANT ALL ON TABLE "public"."invoices" TO "service_role";



GRANT ALL ON TABLE "public"."invoice_summaries" TO "anon";
GRANT ALL ON TABLE "public"."invoice_summaries" TO "authenticated";
GRANT ALL ON TABLE "public"."invoice_summaries" TO "service_role";



GRANT ALL ON TABLE "public"."refresh_tokens" TO "anon";
GRANT ALL ON TABLE "public"."refresh_tokens" TO "authenticated";
GRANT ALL ON TABLE "public"."refresh_tokens" TO "service_role";



GRANT ALL ON TABLE "public"."users" TO "anon";
GRANT ALL ON TABLE "public"."users" TO "authenticated";
GRANT ALL ON TABLE "public"."users" TO "service_role";



GRANT ALL ON TABLE "public"."verification_tokens" TO "anon";
GRANT ALL ON TABLE "public"."verification_tokens" TO "authenticated";
GRANT ALL ON TABLE "public"."verification_tokens" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";



































drop extension if exists "pg_net";



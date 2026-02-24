import React from "react";
import { render, screen } from "@testing-library/react";
import App from "./App";

test("renders invoice generation heading", () => {
  render(<App />);
  const heading = screen.getByText(/Invoice Generation SaaS/i);
  expect(heading).toBeInTheDocument();
});

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "@/auth/AuthContext";
import { RequireAuth } from "@/auth/RequireAuth";
import { LoginPage } from "@/pages/LoginPage";

const { GET, POST } = vi.hoisted(() => ({ GET: vi.fn(), POST: vi.fn() }));

vi.mock("@/api/client", () => ({
  apiClient: { GET, POST },
  apiBaseUrl: "",
  onUnauthorized: vi.fn(),
  readCsrfToken: () => null,
}));

const user = {
  id: 5,
  username: "testheini",
  display_name: "Testheini Testkonto",
  is_admin: false,
  must_change_password: false,
};

function renderApp(initialPath: string): void {
  render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/change-password" element={<p>change password page</p>} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <p>secret timesheet</p>
              </RequireAuth>
            }
          />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("authentication", () => {
  beforeEach(() => {
    GET.mockReset();
    POST.mockReset();
  });

  it("sends anonymous visitors to the login form", async () => {
    GET.mockResolvedValue({ data: undefined, error: { detail: "Not authenticated" } });
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByText("secret timesheet")).not.toBeInTheDocument();
  });

  it("shows the page to a logged-in user", async () => {
    GET.mockResolvedValue({ data: user });
    renderApp("/");
    expect(await screen.findByText("secret timesheet")).toBeInTheDocument();
  });

  it("forces a password change after an admin reset", async () => {
    GET.mockResolvedValue({ data: { ...user, must_change_password: true } });
    renderApp("/");
    expect(await screen.findByText("change password page")).toBeInTheDocument();
    expect(screen.queryByText("secret timesheet")).not.toBeInTheDocument();
  });

  it("logs in with username and password", async () => {
    GET.mockResolvedValue({ data: undefined, error: { detail: "Not authenticated" } });
    POST.mockResolvedValue({ data: user });
    renderApp("/login");

    await userEvent.type(await screen.findByLabelText("Username"), "testheini");
    await userEvent.type(screen.getByLabelText("Password"), "correct-horse-battery");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(POST).toHaveBeenCalledWith("/api/auth/login", {
        body: { username: "testheini", password: "correct-horse-battery" },
      });
    });
    expect(await screen.findByText("secret timesheet")).toBeInTheDocument();
  });

  it("shows the error and clears the password when the login fails", async () => {
    GET.mockResolvedValue({ data: undefined, error: { detail: "Not authenticated" } });
    POST.mockResolvedValue({ data: undefined, error: { detail: "Invalid username or password" } });
    renderApp("/login");

    await userEvent.type(await screen.findByLabelText("Username"), "testheini");
    await userEvent.type(screen.getByLabelText("Password"), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid username or password");
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(screen.queryByText("secret timesheet")).not.toBeInTheDocument();
  });
});

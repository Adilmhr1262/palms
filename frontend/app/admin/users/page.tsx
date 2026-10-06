"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, User, UserRole, api } from "@/lib/api";

const ROLES: UserRole[] = ["admin", "teacher", "student"];

function roleBadge(role: UserRole) {
  const cls =
    role === "admin"
      ? "badge bg-wash text-ink"
      : role === "teacher"
        ? "badge bg-wash text-ink"
        : "badge bg-wash text-muted";
  return <span className={cls}>{role}</span>;
}

type FormState = {
  id?: number;
  full_name: string;
  email: string;
  password: string;
  role: UserRole;
};

const EMPTY_FORM: FormState = {
  full_name: "",
  email: "",
  password: "",
  role: "student",
};

export default function UsersPage() {
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [denied, setDenied] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const me = await api<User>("/auth/me");
      if (me.role !== "admin") {
        setDenied(true);
        return;
      }
      setUsers(await api<User[]>("/users"));
    } catch (e) {
      if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
        setDenied(true);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function openNew() {
    setForm(EMPTY_FORM);
    setFormError("");
    setFormOpen(true);
  }

  function openEdit(u: User) {
    setForm({ id: u.id, full_name: u.full_name, email: u.email, password: "", role: u.role });
    setFormError("");
    setFormOpen(true);
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setFormError("");
    setSaving(true);
    try {
      if (form.id) {
        const patch: Record<string, unknown> = {
          full_name: form.full_name,
          role: form.role,
        };
        if (form.password) patch.password = form.password;
        await api(`/users/${form.id}`, { method: "PATCH", body: JSON.stringify(patch) });
      } else {
        await api("/users", {
          method: "POST",
          body: JSON.stringify({
            full_name: form.full_name,
            email: form.email,
            password: form.password,
            role: form.role,
          }),
        });
      }
      setFormOpen(false);
      await load();
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(u: User) {
    await api(`/users/${u.id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !u.is_active }),
    });
    await load();
  }

  async function signOut() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  if (loading) return <p className="text-muted">Loading users...</p>;
  if (denied)
    return (
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
        <p className="mt-4 text-muted">
          Administrator access required.{" "}
          <button onClick={signOut} className="text-ink underline">
            Sign in with another account
          </button>
        </p>
      </div>
    );

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
          <p className="mt-1 text-sm text-muted">
            Create accounts, assign roles, activate or deactivate.
          </p>
        </div>
        <div className="flex gap-3">
          <button onClick={openNew} className="btn-primary">
            New user
          </button>
          <button onClick={signOut} className="btn-secondary">
            Sign out
          </button>
        </div>
      </div>

      {formOpen && (
        <form
          onSubmit={save}
          className="mb-8 max-w-xl border border-line rounded-md p-6"
        >
          <h2 className="mb-4 text-lg font-semibold">
            {form.id ? "Edit user" : "New user"}
          </h2>
          <div className="mb-4">
            <label className="field-label" htmlFor="full_name">
              Full name
            </label>
            <input
              id="full_name"
              className="field-input"
              required
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            />
          </div>
          {!form.id && (
            <div className="mb-4">
              <label className="field-label" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                type="email"
                className="field-input"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>
          )}
          <div className="mb-4">
            <label className="field-label" htmlFor="password">
              {form.id ? "New password (leave blank to keep)" : "Password"}
            </label>
            <input
              id="password"
              type="password"
              className="field-input"
              required={!form.id}
              minLength={8}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
            <p className="mt-1 text-[13px] text-muted">At least 8 characters.</p>
          </div>
          <div className="mb-6">
            <label className="field-label" htmlFor="role">
              Role
            </label>
            <select
              id="role"
              className="field-input"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          {formError && (
            <p role="alert" className="mb-4 text-sm text-alert">
              {formError}
            </p>
          )}
          <div className="flex gap-3">
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? "Saving..." : "Save"}
            </button>
            <button
              type="button"
              onClick={() => setFormOpen(false)}
              className="btn-secondary"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.full_name}</td>
              <td>{u.email}</td>
              <td>{roleBadge(u.role)}</td>
              <td>
                {u.is_active ? (
                  <span className="badge bg-[#e9f1ea] text-success">Active</span>
                ) : (
                  <span className="badge bg-wash text-muted">Inactive</span>
                )}
              </td>
              <td className="whitespace-nowrap text-right">
                <button
                  onClick={() => openEdit(u)}
                  className="mr-4 text-ink underline"
                >
                  Edit
                </button>
                <button
                  onClick={() => toggleActive(u)}
                  className="text-ink underline"
                >
                  {u.is_active ? "Deactivate" : "Activate"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-4 text-[13px] text-muted">
        Page 1 of 1 &middot; {users.length} users
      </p>
    </div>
  );
}

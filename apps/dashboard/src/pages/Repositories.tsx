import { useEffect, useState } from "react";
import type { RepositoryStats } from "@gitea-pr-manager/shared-types";
import { api } from "../api";

export function RepositoriesPage() {
  const [items, setItems] = useState<RepositoryStats[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.repositories().then(setItems).catch((err: Error) => setError(err.message));
  }, []);

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Repositories</h1>
        <p className="mt-1 text-sm text-slate-500">Review volume and risk by repository.</p>
      </div>
      {error ? <p className="text-red-700">{error}</p> : null}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-3">Repository</th>
              <th className="px-4 py-3">PRs</th>
              <th className="px-4 py-3">Reviews</th>
              <th className="px-4 py-3">Merged</th>
              <th className="px-4 py-3">High risk</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.repository} className="border-t border-slate-100">
                <td className="px-4 py-3 font-medium">{item.repository}</td>
                <td className="px-4 py-3">{item.prs}</td>
                <td className="px-4 py-3">{item.reviews}</td>
                <td className="px-4 py-3">{item.merged}</td>
                <td className="px-4 py-3">{item.high_risk}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

const PLANNED = [
  { name: "Duplicates", detail: "The same merchant, date and total uploaded twice." },
  { name: "Category limits", detail: "For example, a meal over a set amount on one receipt." },
  { name: "Late submissions", detail: "Receipts uploaded long after the purchase date." },
  { name: "Restricted items", detail: "Things the company doesn't reimburse, such as alcohol." },
];

export default function PolicyPage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Policy</h1>
        <p className="mt-1 text-sm text-gray-600">
          Company spending rules, coming in the next update. A rule only flags a receipt for a person to look at;
          it never changes the amounts.
        </p>
      </div>
      <ul className="divide-y divide-gray-100 rounded-xl border border-gray-200 bg-white">
        {PLANNED.map((rule) => (
          <li key={rule.name} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
            <div>
              <p className="font-semibold">{rule.name}</p>
              <p className="text-sm text-gray-600">{rule.detail}</p>
            </div>
            <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">Planned</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

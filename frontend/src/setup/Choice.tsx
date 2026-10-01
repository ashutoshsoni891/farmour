const big = "min-h-14 rounded-xl border-2 px-4 text-lg font-semibold";
const on = "border-green-800 bg-green-800 text-white";
const off = "border-neutral-400 bg-white text-neutral-900";

/** A row of big one-tap answers. */
export function Choice<T extends string>(props: {
  label: string;
  value: T | null;
  options: readonly T[];
  text: (o: T) => string;
  onPick: (o: T) => void;
}) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-1 text-lg font-bold">{props.label}</legend>
      <div className="flex flex-wrap gap-2">
        {props.options.map((o) => (
          <button
            key={o}
            type="button"
            aria-pressed={props.value === o}
            onClick={() => props.onPick(o)}
            className={`${big} ${props.value === o ? on : off}`}
          >
            {props.text(o)}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

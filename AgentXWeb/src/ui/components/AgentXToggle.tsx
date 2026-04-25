import React, { useId } from "react";
import { tokens } from "../tokens";

type Props = {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label: string;
  helper?: string;
};

export function AgentXToggle({ checked, onChange, disabled = false, label, helper }: Props) {
  const helperId = useId();

  return (
    <label className={["agentx-toggle-row", disabled ? "agentx-toggle-row--disabled" : ""].join(" ").trim()}>
      <div className="min-w-0">
        <div className="agentx-toggle-row__label">{label}</div>
        {helper ? <div id={helperId} className="agentx-toggle-row__helper">{helper}</div> : null}
      </div>
      <span className="agentx-toggle-control">
        <input
          type="checkbox"
          role="switch"
          aria-checked={checked}
          aria-label={label}
          aria-describedby={helper ? helperId : undefined}
          checked={checked}
          className="agentx-toggle__input"
          disabled={disabled}
          onChange={(event) => onChange(event.target.checked)}
        />
        <span
          aria-hidden="true"
          className={[tokens.toggle, checked ? "agentx-toggle--on" : "", disabled ? "agentx-toggle--disabled" : ""].join(" ").trim()}
        >
          <span className="agentx-toggle__thumb" />
        </span>
      </span>
    </label>
  );
}

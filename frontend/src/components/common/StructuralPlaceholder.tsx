import "./StructuralPlaceholder.css";

interface StructuralPlaceholderProps {
  message: string;
}

/**
 * Marks an area of the layout that is intentionally unimplemented at this
 * milestone (no charts, no narrative, no risk data yet). Never used to
 * stand in for a real value — only for whole sections pending later work.
 */
export function StructuralPlaceholder({ message }: StructuralPlaceholderProps) {
  return (
    <div className="atlas-structural-placeholder">
      <span>{message}</span>
    </div>
  );
}

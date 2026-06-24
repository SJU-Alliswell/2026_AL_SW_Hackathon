type AddBlockButtonProps = {
  onClick: () => void;
};

export function AddBlockButton({ onClick }: AddBlockButtonProps) {
  return (
    <button className="add-button" type="button" onClick={onClick}>
      +
    </button>
  );
}

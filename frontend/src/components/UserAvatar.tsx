import { resolveAssetUrl } from "../api/client";

type Props = {
  name: string;
  avatarUrl?: string | null;
  className?: string;
};

export function UserAvatar({ name, avatarUrl, className = "avatar" }: Props) {
  const source = resolveAssetUrl(avatarUrl ?? null);
  return (
    <span className={className} aria-label={`${name} avatar`}>
      {source ? <img alt="" src={source} /> : name.trim().slice(0, 1).toUpperCase()}
    </span>
  );
}

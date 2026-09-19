export function authorLabel(author: string, authorName?: string | null): string {
  const name = (authorName || "").trim();
  if (!name || name.toLowerCase() === author.toLowerCase()) {
    return author;
  }
  return `${name} (@${author})`;
}

export function authorFirstName(author: string, authorName?: string | null): string {
  const name = (authorName || "").trim();
  return name || author;
}

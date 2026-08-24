import { COMPOUND_LIBRARY_SIZE, CURATED_REFERENCE_COUNT, compoundPage } from "../../lib/compound-library";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const page = Number(url.searchParams.get("page") ?? 1);
  const pageSize = Number(url.searchParams.get("pageSize") ?? 25);
  const query = url.searchParams.get("query") ?? "";
  const result = compoundPage(page, pageSize, query);
  return Response.json({
    ...result,
    page: Math.max(1, page),
    pageSize: Math.min(100, Math.max(1, pageSize)),
    librarySize: COMPOUND_LIBRARY_SIZE,
    curatedReferenceCount: CURATED_REFERENCE_COUNT,
    remoteSearchMode: "provider-side SmallWorld search of a live 10.10B-entry map",
    boundary: "This route exposes only the bounded 192-record local reference cache. Multi-billion search uses the operator-gated Python ZINC-22 endpoint and imports at most 100 returned structures.",
  });
}

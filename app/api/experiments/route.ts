import { desc, eq } from "drizzle-orm";
import { getDb } from "../../../db";
import { experiments } from "../../../db/schema";

function requestActor(request: Request) {
  return request.headers.get("oai-authenticated-user-email") ?? "demo-researcher@oncogon.local";
}

function publicRecord(row: typeof experiments.$inferSelect) {
  return {
    id: row.id,
    title: row.title,
    cancerType: row.cancerType,
    cellLine: row.cellLine,
    assayType: row.assayType,
    status: row.status,
    reviewStatus: row.reviewStatus,
    actorEmail: row.actorEmail,
    compoundIds: JSON.parse(row.compoundIdsJson) as string[],
    payload: JSON.parse(row.payloadJson) as Record<string, unknown>,
    observationCount: row.observationCount,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  };
}

export async function GET() {
  try {
    const db = await getDb();
    const rows = await db.select().from(experiments).orderBy(desc(experiments.createdAt)).limit(30);
    return Response.json({ experiments: rows.map(publicRecord), persistence: "D1" });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Experiment history unavailable" }, { status: 503 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json() as {
      id?: string; title?: string; cancerType?: string; cellLine?: string; assayType?: string;
      status?: string; reviewStatus?: string; compoundIds?: string[]; payload?: Record<string, unknown>;
      observationCount?: number;
    };
    if (!body.id || !body.title || !body.cellLine || !Array.isArray(body.compoundIds)) {
      return Response.json({ error: "id, title, cellLine and compoundIds are required" }, { status: 400 });
    }
    const now = new Date().toISOString();
    const db = await getDb();
    const [row] = await db.insert(experiments).values({
      id: body.id,
      title: body.title.slice(0, 160),
      cancerType: body.cancerType ?? "NSCLC",
      cellLine: body.cellLine,
      assayType: body.assayType ?? "CellTiter-Glo",
      status: body.status ?? "completed",
      reviewStatus: body.reviewStatus ?? "pending",
      actorEmail: requestActor(request),
      compoundIdsJson: JSON.stringify(body.compoundIds),
      payloadJson: JSON.stringify(body.payload ?? {}),
      observationCount: Math.max(0, body.observationCount ?? 0),
      createdAt: now,
      updatedAt: now,
    }).onConflictDoUpdate({
      target: experiments.id,
      set: {
        status: body.status ?? "completed",
        reviewStatus: body.reviewStatus ?? "pending",
        payloadJson: JSON.stringify(body.payload ?? {}),
        observationCount: Math.max(0, body.observationCount ?? 0),
        updatedAt: now,
      },
    }).returning();
    return Response.json({ experiment: publicRecord(row), persistence: "D1" }, { status: 201 });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Experiment could not be saved" }, { status: 503 });
  }
}

export async function PATCH(request: Request) {
  try {
    const body = await request.json() as { id?: string; reviewStatus?: "approved" | "rejected" | "pending" };
    if (!body.id || !body.reviewStatus) return Response.json({ error: "id and reviewStatus are required" }, { status: 400 });
    const db = await getDb();
    const [row] = await db.update(experiments).set({
      reviewStatus: body.reviewStatus,
      actorEmail: requestActor(request),
      updatedAt: new Date().toISOString(),
    }).where(eq(experiments.id, body.id)).returning();
    if (!row) return Response.json({ error: "Experiment not found" }, { status: 404 });
    return Response.json({ experiment: publicRecord(row), persistence: "D1" });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Review could not be saved" }, { status: 503 });
  }
}

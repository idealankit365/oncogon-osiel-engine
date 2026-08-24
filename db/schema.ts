import { sql } from "drizzle-orm";
import { integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const experiments = sqliteTable("experiments", {
  id: text("id").primaryKey(),
  title: text("title").notNull(),
  cancerType: text("cancer_type").notNull(),
  cellLine: text("cell_line").notNull(),
  assayType: text("assay_type").notNull(),
  status: text("status").notNull(),
  reviewStatus: text("review_status").notNull().default("pending"),
  actorEmail: text("actor_email").notNull().default("anonymous"),
  compoundIdsJson: text("compound_ids_json").notNull(),
  payloadJson: text("payload_json").notNull(),
  observationCount: integer("observation_count").notNull().default(0),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  updatedAt: text("updated_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

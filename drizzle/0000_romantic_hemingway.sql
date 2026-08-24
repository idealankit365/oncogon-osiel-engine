CREATE TABLE `experiments` (
	`id` text PRIMARY KEY NOT NULL,
	`title` text NOT NULL,
	`cancer_type` text NOT NULL,
	`cell_line` text NOT NULL,
	`assay_type` text NOT NULL,
	`status` text NOT NULL,
	`review_status` text DEFAULT 'pending' NOT NULL,
	`actor_email` text DEFAULT 'anonymous' NOT NULL,
	`compound_ids_json` text NOT NULL,
	`payload_json` text NOT NULL,
	`observation_count` integer DEFAULT 0 NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL
);

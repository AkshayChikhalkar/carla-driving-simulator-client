CREATE TABLE "scenarios" (
  "scenario_id" int NOT NULL,
  "session_id" uuid NOT NULL,
  "scenario_name" varchar NOT NULL,
  "start_time" timestamp DEFAULT (now()),
  "end_time" timestamp,
  "status" varchar,
  "scenario_metadata" json,
  PRIMARY KEY ("scenario_id")
);

CREATE TABLE "sensor_data" (
  "id" int NOT NULL,
  "scenario_id" int,
  "session_id" uuid NOT NULL,
  "timestamp" timestamp DEFAULT (now()),
  "sensor_type" varchar,
  "data" json,
  PRIMARY KEY ("id")
);

CREATE TABLE "simulation_metrics" (
  "id" int NOT NULL,
  "scenario_id" int,
  "session_id" uuid NOT NULL,
  "timestamp" timestamp DEFAULT (now()),
  "elapsed_time" float,
  "speed" float,
  "position_x" float,
  "position_y" float,
  "position_z" float,
  "throttle" float,
  "brake" float,
  "steer" float,
  "target_distance" float,
  "target_heading" float,
  "vehicle_heading" float,
  "heading_diff" float,
  "acceleration" float,
  "angular_velocity" float,
  "gear" int,
  "hand_brake" boolean,
  "reverse" boolean,
  "manual_gear_shift" boolean,
  "collision_intensity" float,
  "cloudiness" float,
  "precipitation" float,
  "traffic_count" int,
  "fps" float,
  "event" varchar,
  "event_details" varchar,
  "rotation_x" float,
  "rotation_y" float,
  "rotation_z" float,
  PRIMARY KEY ("id")
);

CREATE TABLE "vehicle_data" (
  "id" int NOT NULL,
  "scenario_id" int,
  "session_id" uuid NOT NULL,
  "timestamp" timestamp DEFAULT (now()),
  "position_x" float,
  "position_y" float,
  "position_z" float,
  "velocity" float,
  "acceleration" float,
  "steering_angle" float,
  "throttle" float,
  "brake" float,
  PRIMARY KEY ("id")
);

ALTER TABLE "sensor_data" ADD FOREIGN KEY ("scenario_id") REFERENCES "scenarios" ("scenario_id");

ALTER TABLE "simulation_metrics" ADD FOREIGN KEY ("scenario_id") REFERENCES "scenarios" ("scenario_id");

ALTER TABLE "vehicle_data" ADD FOREIGN KEY ("scenario_id") REFERENCES "scenarios" ("scenario_id");

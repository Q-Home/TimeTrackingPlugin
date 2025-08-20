// MongoDB initialisatie script ZONDER authenticatie

// Switch naar de timetracking database
db = db.getSiblingDB("timetracking");

// Maak basis collecties aan
db.createCollection("users");
db.createCollection("time_entries");
db.createCollection("projects");
db.createCollection("devices");
db.createCollection("logs");
db.createCollection("badge_logs"); // NIEUW

// Maak indexen aan voor betere performance
db.users.createIndex({ username: 1 }, { unique: true });
db.users.createIndex({ email: 1 }, { unique: true });
db.time_entries.createIndex({ user_id: 1 });
db.time_entries.createIndex({ start_time: 1 });
db.time_entries.createIndex({ end_time: 1 });
db.devices.createIndex({ device_id: 1 }, { unique: true });
db.logs.createIndex({ timestamp: 1 });

// NIEUW: Badge logs indexen
db.badge_logs.createIndex({ badge_code: 1 });
db.badge_logs.createIndex({ timestamp: -1 });
db.badge_logs.createIndex({ username: 1 });
db.badge_logs.createIndex({ user_id: 1 });
db.badge_logs.createIndex({ action: 1 });
db.badge_logs.createIndex({ device_id: 1 });
db.badge_logs.createIndex({ processed: 1 });
db.badge_logs.createIndex({ timestamp: -1, badge_code: 1 });

print("TimeTracking database initialized successfully WITHOUT authentication!");
print("Created collections: users, time_entries, projects, devices, logs, badge_logs");
print("Database is accessible without username/password");

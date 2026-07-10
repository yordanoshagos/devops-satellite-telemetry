// =============================================================================
// k6 load test for the Satellite Telemetry MELT stack.
//
// Scenarios (pick with SCENARIO env var):
//   normal   500 iterations / 10 VUs  - baseline healthy traffic (POST /telemetry)
//   stress   2000 iterations / 50 VUs - pressure: watch latency + error rate
//   failure  300 iterations / 10 VUs  - hammer /fail to trip the error alert
//
// Usage:
//   k6 run -e SCENARIO=normal  scripts/load-test.js
//   k6 run -e SCENARIO=stress  scripts/load-test.js
//   k6 run -e SCENARIO=failure scripts/load-test.js
//   (override target with -e BASE_URL=http://localhost)
// =============================================================================
import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost";
const SCENARIO = __ENV.SCENARIO || "normal";

const profiles = {
  normal: { vus: 10, iterations: 500 },
  stress: { vus: 50, iterations: 2000 },
  failure: { vus: 10, iterations: 300 },
};
const profile = profiles[SCENARIO] || profiles.normal;

export const options = {
  scenarios: {
    [SCENARIO]: {
      executor: "shared-iterations",
      vus: profile.vus,
      iterations: profile.iterations,
      maxDuration: "5m",
    },
  },
  // Only assert latency for non-failure scenarios (failure traffic is expected
  // to be 100% errors, so a latency SLO would be misleading there).
  thresholds:
    SCENARIO === "failure"
      ? {}
      : { http_req_duration: ["p(95)<2000"], http_req_failed: ["rate<0.05"] },
};

const nominalFrame = {
  satellite_id: "SAT-001",
  mission_id: "MISSION-ALPHA-7",
  timestamp: "2026-06-18T09:30:00Z",
  telemetry_frame: {
    battery_voltage: 14.2,
    solar_panel_temp: 45.3,
    gyro_x: 0.01,
    gyro_y: -0.02,
    gyro_z: 0.0,
    signal_strength_dbm: -85,
    downlink_frequency: 437.5,
  },
};

export default function () {
  if (SCENARIO === "failure") {
    const res = http.get(`${BASE_URL}/fail`);
    check(res, { "failure returns 500": (r) => r.status === 500 });
  } else {
    const res = http.post(`${BASE_URL}/telemetry`, JSON.stringify(nominalFrame), {
      headers: { "Content-Type": "application/json" },
    });
    check(res, { "telemetry accepted (202)": (r) => r.status === 202 });
  }
  sleep(0.1);
}
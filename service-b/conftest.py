import os

# Keep unit tests hermetic: no span export to a (non-existent) collector, and
# the lab /slow endpoint should not actually sleep during tests.
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("LAB_SLOW_SECONDS", "0")

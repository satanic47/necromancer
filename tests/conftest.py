import os

# Ensure testing environment variable is set so offline sandboxed test suites
# do not attempt real outbound network socket connections to Sentry or MongoDB Atlas
os.environ["TESTING"] = "1"

# STRICT audit runner rule

Audit runners must be idempotent: they may create timestamped local audit artifacts and refresh their tracked `latest.txt` snapshot, but they must stop output redirection before copying and committing that snapshot.

This prevents `tee` from continuing to modify a file after Git has committed it and keeps the working tree clean after a successful audit.

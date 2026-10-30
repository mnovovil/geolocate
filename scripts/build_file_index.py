"""Scan an Overture release's parquet footers and write the file index Terraform reads.

Run once per release, then commit the result and `terraform -chdir=infra apply`:
    python scripts/build_file_index.py s3://overturemaps-us-west-2/release/<release>/theme=buildings/type=building/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from config import Config  # noqa: E402
from db import connect  # noqa: E402
from file_index import build_index, dumps_index  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", help="S3 folder of the Overture buildings release")
    parser.add_argument("--region", default="us-west-2", help="AWS region of the bucket")
    parser.add_argument("--output", type=Path, default=REPO / "infra/overture_file_index.json")
    args = parser.parse_args(argv)

    # The Overture bucket is public, so the scan never needs credentials.
    con = connect(
        Config(
            overture_buildings_path=args.folder,
            s3_region=args.region,
            aws_access_key_id=None,
            aws_secret_access_key=None,
            aws_session_token=None,
            search_radius_m=100.0,
        )
    )
    index = build_index(con, args.folder)
    args.output.write_text(dumps_index(index))
    print(f"Wrote {len(index['files'])} files to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

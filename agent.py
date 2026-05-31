import argparse
import subprocess
from pathlib import Path
import textwrap


def load_sql_template() -> str:
    sql_path = Path(__file__).parent.parent / "sql" / "incident_history.sql"
    return sql_path.read_text(encoding="utf-8")


def build_query(service_name: str) -> str:
    template = load_sql_template()
    return template.replace(":service_name", f"'{service_name}'")


def run_coral_sql(query: str) -> str:
    result = subprocess.run(
        ["coral", "sql", query],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def main():
    parser = argparse.ArgumentParser(
        description="Incident memory agent backed by Coral + local_incidents"
    )
    parser.add_argument("--service", required=True, help="Service name (e.g. auth-service)")
    args = parser.parse_args()

    print(textwrap.dedent(f"""
        Looking up incident history for service: {args.service}
        (via Coral table local_incidents.incidents)
    """))

    query = build_query(args.service)
    print("SQL being sent to Coral:\n")
    print(query)
    print("\nExecuting query...\n")

    try:
        output = run_coral_sql(query)
        print("=== Coral result ===\n")
        print(output)
        print("\n====================\n")
    except subprocess.CalledProcessError as e:
        print("Error running coral sql:")
        print(e.stderr)


if __name__ == "__main__":
    main()
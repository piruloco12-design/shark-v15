from performance_analyzer import format_performance_report


def main():
    report = format_performance_report(limit=500)
    print(report)


if __name__ == "__main__":
    main()
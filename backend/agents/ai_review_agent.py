def review_codebase(report):
    recommendations = []
    analysis = report.get("analysis", {})
    files = analysis.get("files_found", 0)

    if files == 0:
        recommendations.append(
            "Repository appears empty or could not be scanned."
        )
    else:
        recommendations.append("Repository structure analyzed successfully.")

    recommendations.append(
        "Check dependency versions and deployment configuration."
    )

    return {
        "review_status": "complete",
        "recommendations": recommendations,
        "next_action": "Run debug and deployment agents",
    }

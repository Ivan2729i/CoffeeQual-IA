from collections import Counter

PRIMARY = {"black", "foreign", "infested", "sour"}
SECONDARY = {"broken", "fraghusk", "green", "husk", "immature"}

def grade_from_counts(counts: dict) -> dict:
    primary_total = sum(counts.get(k, 0) for k in PRIMARY)
    secondary_total = sum(counts.get(k, 0) for k in SECONDARY)

    score = primary_total * 3 + secondary_total * 1

    # Umbrales ejemplo (los ajustamos con tus pruebas)
    if score <= 2:
        grade = 1
    elif score <= 6:
        grade = 2
    elif score <= 12:
        grade = 3
    else:
        grade = 4

    return {
        "primary_total": primary_total,
        "secondary_total": secondary_total,
        "score": score,
        "grade": grade,
    }

def counts_from_results(results, names) -> dict:
    boxes = results[0].boxes
    cls_ids = boxes.cls.int().tolist()
    cls_names = [names[i] for i in cls_ids]
    return dict(Counter(cls_names))

"""Tractarian representation model for possible states of affairs and propositions."""

from __future__ import annotations


def configure_state(objects: list[str], relations: list[list[str]]) -> dict:
    if not isinstance(objects, list) or not objects or not all(
        isinstance(item, str) and item.strip() for item in objects
    ):
        raise ValueError("possible state requires non-empty object names")
    if len(set(objects)) != len(objects):
        raise ValueError("possible state object names must be unique")
    normalized_relations = []
    for relation in relations:
        if not isinstance(relation, list) or len(relation) != 3:
            raise ValueError("relations must be subject-predicate-object triples")
        subject, predicate, target = relation
        if subject not in objects or target not in objects:
            raise ValueError("relation endpoints must name configured objects")
        if not isinstance(predicate, str) or not predicate.strip():
            raise ValueError("relation predicate must be non-empty")
        normalized_relations.append([subject, predicate.strip(), target])
    return {"objects": objects, "relations": normalized_relations}


def form_proposition(state: dict, text: str, picture: list[dict]) -> dict:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("proposition text must be non-empty")
    if not isinstance(picture, list) or not all(isinstance(item, dict) for item in picture):
        raise ValueError("proposition picture must be a mapping list")
    elements: set[str] = set()
    pictured: set[str] = set()
    normalized = []
    for mapping in picture:
        if set(mapping) != {"element", "object"}:
            raise ValueError("picture mappings require element and object")
        element, object_name = mapping["element"], mapping["object"]
        if not isinstance(element, str) or not element.strip():
            raise ValueError("picture elements must be non-empty")
        if object_name not in state["objects"]:
            raise ValueError("picture references unknown state object")
        if element in elements or object_name in pictured:
            raise ValueError("picture mapping must be one-to-one")
        elements.add(element); pictured.add(object_name)
        normalized.append({"element": element, "object": object_name})
    if pictured != set(state["objects"]):
        raise ValueError("picture must map every configured object")
    return {"text": text.strip(), "picture": normalized, "sense": "articulated"}


def test_result(result: str, evidence: str) -> dict:
    if result not in {"confirmed", "refuted", "undetermined"}:
        raise ValueError("proposition test result is invalid")
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError("proposition test requires evidence")
    return {"result": result, "evidence": evidence.strip()}

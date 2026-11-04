import argparse
from .sources import acquire, restore


def main():
    parser = argparse.ArgumentParser(description='Versioned Unicode / BabelStone inventory')
    commands = parser.add_subparsers(dest='command', required=True)
    fetch = commands.add_parser('acquire')
    fetch.add_argument('--manifest', default='sources.json')
    fetch.add_argument('--lock', default='sources.lock.json')
    build = commands.add_parser('inventory')
    build.add_argument('--lock', default='sources.lock.json')
    build.add_argument('--output', default='data/generated')
    pinned = commands.add_parser('restore')
    pinned.add_argument('--lock', default='sources.lock.json')
    dump = commands.add_parser('fetch-glyphwiki')
    dump.add_argument('--lock', default='glyphwiki.lock.json')
    index = commands.add_parser('index-glyphwiki')
    index.add_argument('--lock', default='glyphwiki.lock.json')
    index.add_argument('--database', default='data/generated/glyphwiki.sqlite3')
    index.add_argument('--reports', default='reports/generated/glyphwiki')
    candidates = commands.add_parser('candidates')
    candidates.add_argument('--database', default='data/generated/glyphwiki.sqlite3')
    candidates.add_argument('--inventory', default='data/generated/inventory.jsonl')
    candidates.add_argument('--output', default='data/generated')
    resolve = commands.add_parser('resolve')
    resolve.add_argument('reference')
    resolve.add_argument('--database', default='data/generated/glyphwiki.sqlite3')
    resolve.add_argument('--output', required=True)
    review = commands.add_parser('review-inventory')
    review.add_argument('--directory', default='data/generated')
    review.add_argument('--output', default='docs/inventory-review-queue.json')
    audit = commands.add_parser('audit-dependencies')
    audit.add_argument('--database', default='data/generated/glyphwiki.sqlite3')
    audit.add_argument('--candidates', default='data/generated/candidates.jsonl')
    audit.add_argument('--output', default='data/generated/dependency-audit')
    lookup = commands.add_parser('lookup')
    lookup.add_argument('identifier')
    lookup.add_argument('--glyph')
    lookup.add_argument('--database', default='data/generated/glyphwiki.sqlite3')
    lookup.add_argument('--candidates', default='data/generated/mappings.jsonl')
    lookup.add_argument('--output', required=True)
    lookup.add_argument('--dataset', help='Portable SQLite dataset; does not need the upstream index')
    lookup.add_argument('--feature-reviews', help='Pinned, scoped visual observations; does not change mapping decisions')
    release = commands.add_parser('build-release')
    release.add_argument('--directory', default='data/generated')
    release.add_argument('--project', default='.')
    release.add_argument('--output', default='dist/kanji-kage-map-v0.1.sqlite3')
    pua = commands.add_parser('pua-candidates')
    pua.add_argument('--database', default='data/generated/glyphwiki.sqlite3')
    pua.add_argument('--source-rows', default='data/generated/source-rows.jsonl')
    pua.add_argument('--inventory', default='data/generated/inventory.jsonl')
    pua.add_argument('--output', default='data/generated/pua-research')
    assembled = commands.add_parser('assemble')
    assembled.add_argument('--directory', default='data/generated')
    assembled.add_argument('--output', default='data/generated/mappings.jsonl')
    args = parser.parse_args()
    if args.command == 'build-release':
        from .release import build_release
        build_release(args.directory, args.output, args.project)
        return
    if args.command == 'assemble':
        from .assemble import assemble
        assemble(args.directory, args.output)
        return
    if args.command == 'pua-candidates':
        from .pua import discover_pua
        discover_pua(args.database, args.source_rows, args.inventory, args.output)
        return
    if args.command == 'lookup':
        from .lookup import lookup as find
        from .sources import write_json
        if args.dataset:
            from .release import lookup_release
            result = lookup_release(args.dataset, args.identifier, args.glyph)
        else:
            result = find(args.identifier, args.candidates, args.database, args.glyph)
        if args.feature_reviews:
            from .feature_reviews import attach_feature_reviews
            result = attach_feature_reviews(result, args.feature_reviews)
        write_json(args.output, result)
        return
    if args.command == 'audit-dependencies':
        from .audit import audit_dependencies
        audit_dependencies(args.database, args.candidates, args.output)
        return
    if args.command == 'review-inventory':
        from .inventory import classify_issues
        classify_issues(args.directory, args.output)
        return
    if args.command == 'fetch-glyphwiki':
        from .glyphwiki import fetch_dump
        fetch_dump(args.lock)
        return
    if args.command == 'index-glyphwiki':
        from .glyphwiki import index_dump
        index_dump(args.lock, args.database, args.reports)
        return
    if args.command == 'candidates':
        from .glyphwiki import collect_candidates
        collect_candidates(args.database, args.inventory, args.output)
        return
    if args.command == 'resolve':
        from .glyphwiki import resolve_bundle
        from .sources import write_json
        write_json(args.output, resolve_bundle(args.database, args.reference))
        return
    if args.command == 'acquire':
        raise SystemExit(0 if acquire(args.manifest, args.lock) else 1)
    if args.command == 'restore':
        restore(args.lock)
        return
    from .inventory import build_inventory
    build_inventory(args.lock, args.output)


if __name__ == '__main__':
    main()

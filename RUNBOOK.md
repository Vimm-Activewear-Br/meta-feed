# Vimm · Meta square images + supplementary feed

This folder is the git repo github.com/Vimm-Activewear-Br/meta-feed (public; no secrets in here). Locally it lives in
`~/Vimm/meta-feed`. Heavy/local-only folders (src*, out*, review images, Meta reports) are in .gitignore.

**Hourly, no Claude: GitHub Actions** (`.github/workflows/refresh.yml`, cron :17 every hour, also "Run workflow" by hand)
runs `auto_refresh.py`: reads the public storefront + the BAZAR collection (/collections/sale), re-applies the rules,
rebuilds the CSV + `status.json`, and commits only if something changed. Log: `state/auto_refresh.log`.
Things that need Claude become "ação" alerts on the dashboard and go once to Slack (secret `SLACK_WEBHOOK_URL`, channel
#processos) and Todoist (secret `TODOIST_TOKEN`, project PROCESSOS):
Each alert carries the exact command to paste into Claude (also on the dashboard, with a copy button). When the alert
disappears (Claude did the work and pushed → the push triggers the workflow), its Todoist tasks are closed and Slack
gets "✅ Resolvido". Sent alerts + Todoist task ids: `state/notified.json`. Optional repo variable `TODOIST_ASSIGNEES`
(e-mails, comma-separated; one task per person). Alert types:
- new products without square images (`state/pending_new.json`);
- photos changed on Shopify (`state/photos_changed.json`, compared with `state/images_snapshot.json`). After redoing
  those squares, remove the product titles from `state/photos_changed.json`.
Dashboard: `index.html` + `status.json` on GitHub Pages: https://vimm-activewear-br.github.io/meta-feed/
Not visible to it (admin-only): sibling_color, material, aviso_cor, Facebook channel → refreshed when Claude runs.

**Local Claude runs:** always `git pull --rebase origin main` first (the cloud commits every time something changes),
then work, then `./publish_feed.sh` (commit + pull --rebase + push; token in the macOS Keychain).

Turns new product photos (4:5) into 1080×1080 squares by extending the beige backdrop sideways,
hosts them in Shopify Files, and keeps one supplementary-feed CSV that Meta fetches by URL.

**Feed URL (fixed, set once in Meta → supplementary feed, scheduled):**
https://raw.githubusercontent.com/Vimm-Activewear-Br/meta-feed/main/vimm-meta-supplementary-feed.csv
Published by the hourly workflow or by `./publish_feed.sh` after local Claude work. GitHub refreshes the raw file in ~5 min.
(Old: Shopify Files `vimm-meta-supplementary-feed.csv`. Its CDN caches each URL for a year, so it needed a new `?v=` link per update.)
- Columns: `id` (Shopify **variant ID**, confirmed from Meta's error report), `image_link` (always `?format=pjpg`:
  without it Shopify's CDN serves WebP to clients that accept it, and Meta rejects anything but JPEG/PNG),
  `additional_image_link` (comma-separated clean extra squares, `?format=pjpg`), `short_description`
  (from `short_desc.py`, ≤ 60 chars: Meta flagged 80 as too long), `custom_label_0 = vimm_feed`
- Bazar products are left out. The supplementary feed can't remove items, so ads should use a Meta product set:
  `custom_label_0 is vimm_feed` AND `availability is in stock` → only in-stock, non-Bazar items

## Files
| | |
|---|---|
| `square.py` | 4:5 → square by extending each row's backdrop colour outward, soft seam, light grain |
| `edges.py` | scores how much of the left/right margin is body vs plain backdrop |
| `process.py` | new products only: picks the first clean image (or an override), squares it, writes `state/review.jpg` |
| `upload_staged.py` | POSTs files to the targets from a `stagedUploadsCreate` response |
| `build_feed.py` | builds the CSV from `state/uploaded.json` + live variants from the storefront, skipping Bazar |
| `additional.py` | extra photos: squares the clean ones (≠ main) → `state/additional_plan.json`, `out_add/`, `state/review_add.jpg` |
| `feed_attrs.py` | color, size, gender, age_group, material, google_product_category (conjuntos = Outfit Sets), product_type, is_outfit_set, size_system, custom_label_1 = principal/variante (1 tamanho do meio em estoque por produto), custom_label_2–4 |
| `short_desc.py` | short_description per product type, ≤ 60 chars |
| `state/bazar.json` | ACTIVE products in the BAZAR collection |
| `state/rules.json` | who's left out of the feed: id list, min price, test words, tags |
| `refresh_products.py` | storefront → `state/products.json` (in scope) + `state/excluded.json` (with reason) |
| `state/products.json` | products to consider (id, title, media[] with mid/url/w/h) |
| `state/uploaded.json` | done products → square image URL, source image |
| `state/overrides.json` | `{ "<productId>": <image index> }` to force a specific photo |
| `state/since.txt` | date of the last run; products created after it are "new" |

## Routine (each run)
1. Refresh `state/bazar.json` with the ACTIVE products of the BAZAR collection (gid://shopify/Collection/439003840750),
   then `python3 refresh_products.py`. It applies `state/rules.json` (exclusion list, Bazar, price < min_price,
   test words in the title, blocked tags such as `nao-meta`) and writes `state/products.json` + `state/excluded.json`.
   process.py skips products already in uploaded.json.
   Also refresh `state/attrs.json` (all ACTIVE products: title, productType, tags, metafields theme.sibling_color,
   custom.material_e_cuidados, custom.aviso_cor). The query is big, so the connector saves it to a file; convert it
   with the same shape as today ({productId: {title,type,tags,color,material,aviso,options}}). feed_attrs.py reads it.
2. `python3 process.py`, then **look at `state/review.jpg`**. Reject any pick that has a body part cut
   at a side, text overlays (e.g. "curtinha/original"), or is a tight detail crop when a full-body shot exists;
   set an override in `state/overrides.json` and run again.
3. `stagedUploadsCreate` (resource IMAGE, image/jpeg, POST) with filenames `meta-sq-<productId>-<sourceMediaId>.jpg`,
   save the response to a JSON file, `python3 upload_staged.py that.json`, then `fileCreate` (contentType IMAGE).
   Extra photos: `python3 additional.py`, look at `state/review_add.jpg` (same rules; text overlays are OK on extras),
   upload `state/additional_todo.json` as `meta-sq-add-<key>.jpg` (same staged flow), then add each key → cdn URL
   (no query) to `state/additional_uploaded.json`.
4. Query `files(query:"filename:meta-sq-<productId>*")` for the cdn URLs; add entries to `state/uploaded.json`.
5. Check which ACTIVE products are NOT published on the "Facebook & Instagram" publication
   (gid://shopify/Publication/119421960430, field publishedOnPublication) and list them in the report: they aren't in the
   Meta catalog, so their rows produce "ID não coincide" until someone publishes them. Also report products that ARE
   on that channel but are in `state/excluded.json`: they're still in the Meta catalog, so someone has to unpublish
   them in Shopify (the connector blocks unpublishing). Ads stay safe meanwhile via the vimm_feed product set. Then `python3 build_feed.py`; upload `meta_supplementary_feed.csv` via staged upload (resource FILE, text/csv,
   filename `vimm-meta-supplementary-feed.csv`) and `fileUpdate` the feed file id above.
6. Write today's date to `state/since.txt`.

(Before step 5's build: refresh `state/not_on_fb.json` with ACTIVE products not on the Facebook & Instagram
channel. build_feed.py leaves them out, since rows for items missing from the catalog only produce "ID não coincide".)

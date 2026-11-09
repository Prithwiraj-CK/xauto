# Post package and evidence review

All daily and manual `send_post.py` drafts must declare `content_kind`: `opinion`,
`reaction`, `research`, `investigation`, or `journey`. This describes the content;
`type` still follows the existing weekday topic. Scheduled daily posts must be original and may not use quote tweets; the reaction rules below remain for manual posts. Do not classify factual reporting
as opinion to avoid proof checks. JSON `note` is internal and is never a source reply.

## Required review before saving a draft

1. Read `content/VOICE.md`. Pick one finding or concrete disagreement relevant to
   Solana, Meteora or the scheduled niche. State the actual point without a required
   slogan, first-person line or closing question. Most posts fit around 250 characters.
   Put transaction detail in the receipt reply. Never invent a position, loss,
   conversation, wallet owner or first-hand discovery.
2. Read the original statement and primary evidence. Verify the handle through the
   original post/profile. Separate wallet links from wallet ownership, transfers from
   sales, reported allegations from verified findings, and selected examples from a full
   dataset. Attribute another investigator's work in the main text. Show the event date
   in the main post or source reply when covering older evidence. Do not imply old news
   is a new discovery. Do not force an accusation when the receipts don't support one.
3. For reactions, quote the exact statement being discussed and actually @mention its
   author in the text. Declare that URL as both `source_tweet_url` and `quote_tweet_url`,
   and list the relevant people/projects in `subject_handles` without the @ prefix.
   Investigations must also have screenshot/image receipts. If there is no original
   statement, quote the primary investigation and credit its author, with the subject
   tagged as relevant. Maximum two mentions. A plain name or URL is not an @mention.
4. Capture authentic explorer/chart/source images. Open every final local file and
   visually inspect it. Put the strongest readable receipt first, at most four images.
   Include enough source context, wallet/token identity, units and timestamp to interpret
   the claim. Use an actual QT for a tweet reaction; tweet screenshots cannot substitute
   for it. Images AND quote tweets are supported together.
5. No AI-generated evidence, fabricated screenshots, recreated transactions, synthetic
   photos, or misleading crops. Prefer unchanged original images. Charts generated from
   real data need reproducible source data and must be identified as charts, not screenshots.
   If a screenshot is unreadable, recapture it or choose a clearer real receipt. Never mark
   a visual reviewed based only on a filename or successful download.
   Exclude private messages, credentials and unrelated personal browser/account details.
6. After visual review, record the SHA256 of the exact bytes to upload. Attach provenance
   below. The publisher checks the hash again before upload. It cannot itself prove that
   a screenshot is truthful: research and visual review are mandatory.
7. `source_reply` is actual public text, up to 700 characters. Include image source links,
   credits, material limitations and the event date when relevant. Avoid repeating the
   main text or narrating the internal review. The publisher posts it under the
   main tweet and verifies its parent. Do not ask for a source reply only in `note`.

## JSON shape (illustrative placeholders, never publish them)

```json
{
  "type": "hot-take",
  "content_kind": "investigation",
  "text": "<concrete finding or disagreement with @subject and attribution>",
  "subject_handles": ["subject"],
  "source_tweet_url": "https://x.com/subject/status/123",
  "quote_tweet_url": "https://x.com/subject/status/123",
  "images": ["out/proof/receipt.png"],
  "sources": [
    {"url": "https://x.com/subject/status/123", "claim": "<exact public claim>", "checked_at": "<ISO timestamp with timezone>"},
    {"url": "https://<primary explorer or investigation URL>", "claim": "<what this evidence actually establishes>", "checked_at": "<ISO timestamp with timezone>"}
  ],
  "image_proof": [{
    "path": "out/proof/receipt.png",
    "kind": "screenshot",
    "source_url": "https://<primary explorer or investigation URL>",
    "claim": "<specific fact visible in this image>",
    "credit": "<source/investigator>",
    "captured_at": "<ISO timestamp with timezone>",
    "sha256": "<64-character digest of the reviewed file>",
    "visual_review": {"readable": true, "authentic": true, "supports_claim": true}
  }],
  "source_reply": "<event date, attribution, limitations and image source URLs>",
  "note": "<internal editorial context only>"
}
```

`image_proof.kind` accepts `screenshot`, `source_image` (another source's original
image, with credit) and `data_chart`. Every image source URL must also occur in
`sources` and in the public `source_reply`. All timestamps need timezones.
Use `sources` for factual research even if it has only a QT and no images.
Plain opinions/journey posts can omit sources/images when they make no factual claims
requiring receipts. Self-followups can use `opinion` with a QT, without tagging yourself.

Validate with `scheduled_run.validate_post(post, target_date)` before returning the
draft. Never run a publisher from the drafting session.

## Publication checks

The publisher sends the quote URL and media IDs together. After publication it reads
the tweet back and checks account, text, quote ID, image count, and actual mention
entities. It saves tweet IDs under `out/publications/` before read-back checks, so a
read failure or missing attachment cannot silently cause a duplicate post. Source
replies have separate saved IDs and parent checks. An uncertain write blocks retries
until inspected; never clear that state or delete/repost automatically.

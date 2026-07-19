-- Lidl codeInput/data-art-id kann eine interne Artikelkennung statt einer GTIN sein.
-- Reine Informationswarnungen dürfen bestehende Belege nicht prüfpflichtig halten.
WITH valid_warning_arrays AS MATERIALIZED (
  SELECT id, warnings_json
  FROM module_haushaltsbuch_loyalty_receipts
  WHERE json_valid(warnings_json)
    AND json_type(warnings_json) = 'array'
)
UPDATE module_haushaltsbuch_loyalty_receipts
SET validation_status = 'valid'
WHERE validation_status = 'needs_review'
  AND id IN (
    SELECT receipt.id
    FROM valid_warning_arrays AS receipt
    WHERE EXISTS (
      SELECT 1 FROM json_each(receipt.warnings_json)
      WHERE json_each.type = 'text' AND json_each.value = 'invalid_gtin'
    )
      AND NOT EXISTS (
        SELECT 1 FROM json_each(receipt.warnings_json)
        WHERE json_each.type <> 'text'
           OR json_each.value NOT IN (
             'currency_inferred_de',
             'timezone_inferred_de',
             'total_discount_derived',
             'coupon_metadata_without_amount',
             'invalid_gtin'
           )
      )
  );

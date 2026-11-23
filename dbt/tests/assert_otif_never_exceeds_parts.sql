-- A line cannot be OTIF without being in full, and order OTIF cannot exceed line OTIF.
select order_line_id from {{ ref('fct_order_line') }} where is_otif_original and not is_in_full

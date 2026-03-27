WITH "CTE_LastValidation_Time" AS (
    SELECT 
        "XLA_TRANSACTION_ENTITIES"."TransactionSourceIdInt1" AS "INVOICE_ID",
        ROW_NUMBER() OVER (
            PARTITION BY "XLA_TRANSACTION_ENTITIES"."TransactionSourceIdInt1"
            ORDER BY "XLA_EVENTS"."EventPEOCreationDate" ASC, "XLA_EVENTS"."EventPEOEventNumber" DESC
        ) AS "rn",
        CAST("XLA_EVENTS"."EventPEOEventDate" AS TIMESTAMP) AS "LastValidationTime",
        "XLA_EVENTS"."EventPEOEventId" AS "EVENT_ID",
        "XLA_EVENTS"."EventPEOEventPEOCreatedBy" AS "CREATED_BY"
    FROM "FscmTopModelAM_FinExtractAM_XlaBiccExtractAM_SubledgerJournalTransactionEntityExtractPVO" AS "XLA_TRANSACTION_ENTITIES"
    LEFT JOIN "FscmTopModelAM_FinExtractAM_XlaBiccExtractAM_SubledgerJournalEventExtractPVO" AS "XLA_EVENTS"
        ON "XLA_TRANSACTION_ENTITIES"."TransactionApplicationId" = "XLA_EVENTS"."EventPEOApplicationId"
        AND "XLA_TRANSACTION_ENTITIES"."TransactionEntityId" = "XLA_EVENTS"."EventPEOEntityId"
    WHERE "XLA_TRANSACTION_ENTITIES"."TransactionEntityCode" = 'AP_INVOICES'
        AND "XLA_TRANSACTION_ENTITIES"."TransactionApplicationId" = 200
        AND "XLA_EVENTS"."EventPEOEventStatusCode" = 'P'
        AND "XLA_EVENTS"."EventPEOEventTypeCode" IN ('CREDIT MEMO CANCELLED', 'DEBIT MEMO CANCELLED')
),
"CTE_LastValidation" AS (
    SELECT 
        "LastValTime"."INVOICE_ID",
        "LastValTime"."LastValidationTime",
        "LastValTime"."CREATED_BY",
        "LastValTime"."EVENT_ID"
    FROM "CTE_LastValidation_Time" AS "LastValTime"
    WHERE "LastValTime"."rn" = 1
),
"CTE_FullValidation" AS (
    SELECT "AP_INVOICE_DISTRIBUTIONS_ALL"."ApInvoiceDistributionsInvoiceId" AS "INVOICE_ID"
    FROM "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_InvoiceDistributionExtractPVO" AS "AP_INVOICE_DISTRIBUTIONS_ALL"
    WHERE "AP_INVOICE_DISTRIBUTIONS_ALL"."ApInvoiceDistributionsPostedFlag" = 'Y'
    EXCEPT
    SELECT "AP_INVOICE_DISTRIBUTIONS_ALL"."ApInvoiceDistributionsInvoiceId" AS "INVOICE_ID"
    FROM "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_InvoiceDistributionExtractPVO" AS "AP_INVOICE_DISTRIBUTIONS_ALL"
    WHERE "AP_INVOICE_DISTRIBUTIONS_ALL"."ApInvoiceDistributionsPostedFlag" <> 'Y'
),
"CTE_AGG_INV_PAYM" AS (
    SELECT 
        "ApInvoicePaymentsAllInvoiceId" AS "INVOICE_ID",
        "ApInvoicePaymentsAllPaymentNum" AS "PAYMENT_NUM",
        COALESCE(SUM("ApInvoicePaymentsAllDiscountTaken"), 0) AS "DISCOUNT_TAKEN",
        COALESCE(SUM("ApInvoicePaymentsAllDiscountLost"), 0) AS "DISCOUNT_LOST",
        MAX("ApInvoicePaymentsAllCreationDate") AS "PAYMENT_DATE"
    FROM "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_PaidDisbursementScheduleExtractPVO" AS "AP_INVOICE_PAYMENTS_ALL"
    GROUP BY "ApInvoicePaymentsAllInvoiceId", "ApInvoicePaymentsAllPaymentNum"
),
"CTE_PERIOD_LOOKUP" AS (
    SELECT 
        "AP_INVOICE_DISTRIBUTIONS_ALL"."ApInvoiceDistributionsInvoiceId" AS "INVOICE_ID",
        MIN(CAST("GL_PERIOD_STATUSES"."GlPeriodStatusesPeriodYear" AS INTEGER)) AS "PERIOD_YEAR"
    FROM "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_InvoiceDistributionExtractPVO" AS "AP_INVOICE_DISTRIBUTIONS_ALL"
    LEFT JOIN "FscmTopModelAM_FinExtractAM_GlBiccExtractAM_PeriodStatusExtractPVO" AS "GL_PERIOD_STATUSES"
        ON "AP_INVOICE_DISTRIBUTIONS_ALL"."ApInvoiceDistributionsPeriodName" = "GL_PERIOD_STATUSES"."GlPeriodStatusesPeriodName"
        AND "AP_INVOICE_DISTRIBUTIONS_ALL"."ApInvoiceDistributionsSetOfBooksId" = "GL_PERIOD_STATUSES"."GlPeriodStatusesSetOfBooksId"
    GROUP BY "AP_INVOICE_DISTRIBUTIONS_ALL"."ApInvoiceDistributionsInvoiceId"
),
"CTE_TERMS" AS (
    SELECT 
        "AP_TERMS_LINES"."ApTermsLinesTermId" AS "TERM_ID",
        "AP_TERMS_LINES"."ApTermsLinesSequenceNum" AS "SEQUENCE_NUM",
        "AP_TERMS_LINES"."ApTermsLinesDiscountDayOfMonth" AS "DISCOUNT_DAY_OF_MONTH1",
        "AP_TERMS_LINES"."ApTermsLinesDiscountDays" AS "DISCOUNT_DAYS1",
        "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward" AS "DISCOUNT_MONTHS_FORWARD1",
        CAST(COALESCE("AP_TERMS_LINES"."ApTermsLinesDiscountPercent", 0.0) AS DOUBLE) AS "DISCOUNT_PERCENT1",
        "AP_TERMS_LINES"."ApTermsLinesDiscountDayOfMonth2" AS "DISCOUNT_DAY_OF_MONTH2",
        "AP_TERMS_LINES"."ApTermsLinesDiscountDays2" AS "DISCOUNT_DAYS2",
        "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward2" AS "DISCOUNT_MONTHS_FORWARD2",
        CAST(COALESCE("AP_TERMS_LINES"."ApTermsLinesDiscountPercent2", 0.0) AS DOUBLE) AS "DISCOUNT_PERCENT2",
        "AP_TERMS_LINES"."ApTermsLinesDiscountDayOfMonth3" AS "DISCOUNT_DAY_OF_MONTH3",
        "AP_TERMS_LINES"."ApTermsLinesDiscountDays3" AS "DISCOUNT_DAYS3",
        "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward3" AS "DISCOUNT_MONTHS_FORWARD3",
        CAST(COALESCE("AP_TERMS_LINES"."ApTermsLinesDiscountPercent3", 0.0) AS DOUBLE) AS "DISCOUNT_PERCENT3",
        "AP_TERMS_LINES"."ApTermsLinesFixedDate" AS "DUE_DATE",
        "AP_TERMS_LINES"."ApTermsLinesDueDayOfMonth" AS "DUE_DAY_OF_MONTH",
        "AP_TERMS_LINES"."ApTermsLinesDueDays" AS "DUE_DAYS",
        "AP_TERMS_LINES"."ApTermsLinesDueMonthsForward" AS "DUE_MONTHS_FORWARD",
        CASE
            WHEN "AP_TERMS_LINES"."ApTermsLinesDueDays" IS NOT NULL THEN 1
            WHEN "AP_TERMS_LINES"."ApTermsLinesFixedDate" IS NOT NULL THEN 2
            WHEN "AP_TERMS_LINES"."ApTermsLinesDueDayOfMonth" IS NOT NULL
                 AND "AP_TERMS_LINES"."ApTermsLinesDueMonthsForward" IS NOT NULL THEN 3
            WHEN "AP_TERMS_LINES"."ApTermsLinesDueDayOfMonth" IS NULL
                 AND "AP_TERMS_LINES"."ApTermsLinesDueDays" IS NULL
                 AND "AP_TERMS_LINES"."ApTermsLinesDueMonthsForward" IS NULL THEN 4
            ELSE 5 
        END AS "DUEDATEMODE",
        CASE
            WHEN "AP_TERMS_LINES"."ApTermsLinesDiscountDays" IS NOT NULL THEN 1
            WHEN "AP_TERMS_LINES"."ApTermsLinesDueDayOfMonth" IS NOT NULL
                 AND "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward" IS NOT NULL THEN 3
            WHEN "AP_TERMS_LINES"."ApTermsLinesDueDayOfMonth" IS NULL
                 AND "AP_TERMS_LINES"."ApTermsLinesDueDays" IS NULL
                 AND "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward" IS NULL THEN 4
            ELSE 5 
        END AS "DISCOUNTDATEMODE1",
        CASE
            WHEN "AP_TERMS_LINES"."ApTermsLinesDiscountDays2" IS NOT NULL THEN 1
            WHEN "AP_TERMS_LINES"."ApTermsLinesDiscountDayOfMonth2" IS NOT NULL
                 AND "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward2" IS NOT NULL THEN 3
            WHEN "AP_TERMS_LINES"."ApTermsLinesDiscountDayOfMonth2" IS NULL
                 AND "AP_TERMS_LINES"."ApTermsLinesDiscountDays2" IS NULL
                 AND "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward2" IS NULL THEN 4
            ELSE 5 
        END AS "DISCOUNTDATEMODE2",
        CASE
            WHEN "AP_TERMS_LINES"."ApTermsLinesDiscountDays3" IS NOT NULL THEN 1
            WHEN "AP_TERMS_LINES"."ApTermsLinesDiscountDayOfMonth3" IS NOT NULL
                 AND "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward3" IS NOT NULL THEN 3
            WHEN "AP_TERMS_LINES"."ApTermsLinesDiscountDayOfMonth3" IS NULL
                 AND "AP_TERMS_LINES"."ApTermsLinesDiscountDays3" IS NULL
                 AND "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward3" IS NULL THEN 4
            ELSE 5 
        END AS "DISCOUNTDATEMODE3"
    FROM "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_PaymentTermLineExtractPVO" AS "AP_TERMS_LINES"
),
"CTE_SUPPLIER_INFO" AS (
    SELECT 
        "AP_SUPPLIER_SITES_ALL"."VendorSiteId" AS "VENDOR_SITE_ID",
        "AP_SUPPLIERS"."VendorId" AS "VENDOR_ID",
        "AP_SUPPLIER_SITES_ALL"."TermsId" AS "TERMS_ID"
    FROM "FscmTopModelAM_PrcExtractAM_PozBiccExtractAM_SupplierSiteExtractPVO" AS "AP_SUPPLIER_SITES_ALL"
    LEFT JOIN "FscmTopModelAM_PrcPozPublicViewAM_SupplierPVO" AS "AP_SUPPLIERS"
        ON "AP_SUPPLIER_SITES_ALL"."VendorId" = "AP_SUPPLIERS"."VendorId"
    WHERE "AP_SUPPLIERS"."VendorId" IS NOT NULL
),
"CTE_PORELATED" AS (
    SELECT 
        "AP_INVOICE_LINES_ALL"."ApInvoiceLinesAllInvoiceId" AS "INVOICE_ID",
        CASE
            WHEN COUNT("AP_INVOICE_LINES_ALL"."ApInvoiceLinesAllPoHeaderId") > 0 THEN 'Y'
            ELSE 'N' 
        END AS "PO_RELATED_FLAG"
    FROM "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_InvoiceLineExtractPVO" AS "AP_INVOICE_LINES_ALL"
    GROUP BY "AP_INVOICE_LINES_ALL"."ApInvoiceLinesAllInvoiceId"
)
-- ,
-- "Test" AS (
SELECT DISTINCT
    <%=sourceSystem%> || 'VendorAccountCreditItem_' || "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllInvoiceId" || '_' || "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllPaymentNum" AS "ID",
    INV."attachment_link" AS "AttachmentLink",
    INV."cfdi_content" AS "CFDI",
    CASE
        WHEN "NEW_INV_HEADER"."InvoiceHeaderSource" = 'CARGA INICIAL' THEN 'X' 
        ELSE 'No'
    END AS "CargaInicial",
    ApInvoicesApprovalStatus AS Cancelado,

    CASE
        WHEN COALESCE(
            CAST(INV."suppliernumber" AS VARCHAR),
            <%=sourceSystem%> || 'Vendor_' || "AP_INVOICES_ALL"."ApInvoicesVendorSiteId"
        ) IN (
            '0000040202',
            '0000018026',
            '0000019483',
            'Vendor_GPCAT-0000040202',
            'Vendor_GPCAT-0000018026',
            'Vendor_GPCAT-0000019483'
        ) THEN 'Yes'
        ELSE 'No'
    END AS "Cheque",

    -- 1. ASSOCIATION: DocumentDate - invoice_date
    COALESCE(CAST(INV."invoice_date" AS TIMESTAMP), CAST("AP_INVOICES_ALL"."ApInvoicesInvoiceDate" AS TIMESTAMP)) AS "DocumentDateCombinado",
    
    -- 2. ASSOCIATION: ReferenceDocumentNumber - invoice_number
    COALESCE(CAST(INV."invoice_number" AS VARCHAR(255)), "AP_INVOICES_ALL"."ApInvoicesInvoiceNum") AS "ReferenceDocumentNumberCombinado",
    
    -- 3. ASSOCIATION: Vendor_ID (Alias "Vendor") - suppliernumber
    COALESCE(CAST(INV."suppliernumber" AS VARCHAR), <%=sourceSystem%> || 'Vendor_' || "AP_INVOICES_ALL"."ApInvoicesVendorSiteId") AS "VendorCombinado",
    
    -- 4. ASSOCIATION: Amount - amount_paid
    COALESCE(INV."amount_paid", "AP_INVOICES_ALL"."ApInvoicesInvoiceAmount") AS "AmountCombinado",
    
    -- 5. ASSOCIATION: Currency - invoice_currency
    COALESCE(INV."invoice_currency", "AP_INVOICES_ALL"."ApInvoicesInvoiceCurrencyCode") AS "CurrencyCombinado",
    
    -- 6. ASSOCIATION: CompanyCodeText - business_unit
    COALESCE(CAST(INV."business_unit" AS VARCHAR), "HR_ALL_ORGANIZATION_UNITS"."FunBuPerfPEOName") AS "CompanyCodeTextCombinado"

FROM "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_InvoicePaymentScheduleExtractPVO" AS "AP_PAYMENT_SCHEDULES_ALL"
LEFT JOIN "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_InvoiceHeaderExtractPVO" AS "AP_INVOICES_ALL"
    ON "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllInvoiceId" = "AP_INVOICES_ALL"."ApInvoicesInvoiceId"
LEFT JOIN "FscmTopModelAM_FinApInvTransactionsAM_InvoiceHeaderPVO" AS "NEW_INV_HEADER"
    ON "AP_INVOICES_ALL"."ApInvoicesInvoiceId" = "NEW_INV_HEADER"."InvoiceId"
LEFT JOIN <%=DATASOURCE:CLOUDERA_CLOUDERA_TEST%>."Invoice" INV
    ON "AP_INVOICES_ALL"."ApInvoicesInvoiceId" = INV."invoice_id"
LEFT JOIN "CTE_LastValidation" AS "LastValidation"
    ON "AP_INVOICES_ALL"."ApInvoicesInvoiceId" = "LastValidation"."INVOICE_ID"
LEFT JOIN "CTE_FullValidation" AS "FullValidation"
    ON "AP_INVOICES_ALL"."ApInvoicesInvoiceId" = "FullValidation"."INVOICE_ID"
WHERE 1=1  
    AND INV."cfdi_content" IS NOT NULL
    AND "AP_INVOICES_ALL"."ApInvoicesInvoiceTypeLookupCode" IN ('CREDIT', 'DEBIT')
    AND "LastValidation"."INVOICE_ID" IS NOT NULL
    AND "FullValidation"."INVOICE_ID" IS NOT NULL
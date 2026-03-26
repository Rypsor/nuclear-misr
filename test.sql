WITH "CTE_LastValidation_Time" AS (SELECT "XLA_TRANSACTION_ENTITIES"."TransactionSourceIdInt1"                                           AS "INVOICE_ID",
                                          ROW_NUMBER()
                                          OVER (PARTITION BY "XLA_TRANSACTION_ENTITIES"."TransactionSourceIdInt1"
                                              ORDER BY "XLA_EVENTS"."EventPEOCreationDate" ASC, "XLA_EVENTS"."EventPEOEventNumber" DESC) AS "rn",
                                          CAST("XLA_EVENTS"."EventPEOCreationDate" AS TIMESTAMP)                                         AS "LastValidationTime",
                                          "XLA_EVENTS"."EventPEOEventId"                                                                 AS "EVENT_ID",
                                          "XLA_EVENTS"."EventPEOEventPEOCreatedBy"                                                       AS "CREATED_BY"
                                   FROM "FscmTopModelAM_FinExtractAM_XlaBiccExtractAM_SubledgerJournalTransactionEntityExtractPVO" AS "XLA_TRANSACTION_ENTITIES"
                                            LEFT JOIN "FscmTopModelAM_FinExtractAM_XlaBiccExtractAM_SubledgerJournalEventExtractPVO" AS "XLA_EVENTS"
                                                      ON "XLA_TRANSACTION_ENTITIES"."TransactionApplicationId"
                                                         = "XLA_EVENTS"."EventPEOApplicationId"
                                                          AND "XLA_TRANSACTION_ENTITIES"."TransactionEntityId"
                                                              = "XLA_EVENTS"."EventPEOEntityId"
                                   WHERE "XLA_TRANSACTION_ENTITIES"."TransactionEntityCode" = 'AP_INVOICES'
                                     AND "XLA_TRANSACTION_ENTITIES"."TransactionApplicationId" = 200
                                     AND "XLA_EVENTS"."EventPEOEventStatusCode" = 'P'
                                     AND "XLA_EVENTS"."EventPEOEventTypeCode" = 'INVOICE VALIDATED'),
     "CTE_LastValidation" AS (SELECT "LastValTime"."INVOICE_ID",
                                     "LastValTime"."LastValidationTime",
                                     "LastValTime"."CREATED_BY",
                                     "LastValTime"."EVENT_ID"
                              FROM "CTE_LastValidation_Time" AS "LastValTime"
                              WHERE "LastValTime"."rn" = 1),
     "CTE_FullValidation" AS (SELECT "AP_INVOICE_DISTRIBUTIONS_ALL"."ApInvoiceDistributionsInvoiceId" AS "INVOICE_ID"
                              FROM "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_InvoiceDistributionExtractPVO" AS "AP_INVOICE_DISTRIBUTIONS_ALL"
                              WHERE "AP_INVOICE_DISTRIBUTIONS_ALL"."ApInvoiceDistributionsPostedFlag" = 'Y'
                              EXCEPT
                              SELECT "AP_INVOICE_DISTRIBUTIONS_ALL"."ApInvoiceDistributionsInvoiceId" AS "INVOICE_ID"
                              FROM "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_InvoiceDistributionExtractPVO" AS "AP_INVOICE_DISTRIBUTIONS_ALL"
                              WHERE "AP_INVOICE_DISTRIBUTIONS_ALL"."ApInvoiceDistributionsPostedFlag" <> 'Y'),
     "CTE_AGG_INV_PAYM" AS (SELECT "ApInvoicePaymentsAllInvoiceId"                       AS "INVOICE_ID",
                                   "ApInvoicePaymentsAllPaymentNum"                      AS "PAYMENT_NUM",
                                   COALESCE(SUM("ApInvoicePaymentsAllDiscountTaken"), 0) AS "DISCOUNT_TAKEN",
                                   COALESCE(SUM("ApInvoicePaymentsAllDiscountLost"), 0)  AS "DISCOUNT_LOST",
                                   MAX("ApInvoicePaymentsAllCreationDate")               AS "PAYMENT_DATE"
                            FROM "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_PaidDisbursementScheduleExtractPVO" AS "AP_INVOICE_PAYMENTS_ALL"
                            GROUP BY "ApInvoicePaymentsAllInvoiceId", "ApInvoicePaymentsAllPaymentNum"),
     "CTE_PERIOD_LOOKUP" AS (SELECT "AP_INVOICE_DISTRIBUTIONS_ALL"."ApInvoiceDistributionsInvoiceId"        AS "INVOICE_ID",
                                    MIN(CAST("GL_PERIOD_STATUSES"."GlPeriodStatusesPeriodYear" AS INTEGER)) AS "PERIOD_YEAR"
                             FROM "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_InvoiceDistributionExtractPVO" AS "AP_INVOICE_DISTRIBUTIONS_ALL"
                                      LEFT JOIN "FscmTopModelAM_FinExtractAM_GlBiccExtractAM_PeriodStatusExtractPVO" AS "GL_PERIOD_STATUSES"
                                                ON "AP_INVOICE_DISTRIBUTIONS_ALL"."ApInvoiceDistributionsPeriodName"
                                                   = "GL_PERIOD_STATUSES"."GlPeriodStatusesPeriodName"
                                                    AND
                                                   "AP_INVOICE_DISTRIBUTIONS_ALL"."ApInvoiceDistributionsSetOfBooksId"
                                                   = "GL_PERIOD_STATUSES"."GlPeriodStatusesSetOfBooksId"
                             GROUP BY "AP_INVOICE_DISTRIBUTIONS_ALL"."ApInvoiceDistributionsInvoiceId"),
     "CTE_TERMS" AS (SELECT "AP_TERMS_LINES"."ApTermsLinesTermId"                                          AS "TERM_ID",
                            "AP_TERMS_LINES"."ApTermsLinesSequenceNum"                                     AS "SEQUENCE_NUM",
                            "AP_TERMS_LINES"."ApTermsLinesDiscountDayOfMonth"                              AS "DISCOUNT_DAY_OF_MONTH1",
                            "AP_TERMS_LINES"."ApTermsLinesDiscountDays"                                    AS "DISCOUNT_DAYS1",
                            "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward"                           AS "DISCOUNT_MONTHS_FORWARD1",
                            CAST(COALESCE("AP_TERMS_LINES"."ApTermsLinesDiscountPercent", 0.0) AS DOUBLE)  AS "DISCOUNT_PERCENT1",
                            "AP_TERMS_LINES"."ApTermsLinesDiscountDayOfMonth2"                             AS "DISCOUNT_DAY_OF_MONTH2",
                            "AP_TERMS_LINES"."ApTermsLinesDiscountDays2"                                   AS "DISCOUNT_DAYS2",
                            "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward2"                          AS "DISCOUNT_MONTHS_FORWARD2",
                            CAST(COALESCE("AP_TERMS_LINES"."ApTermsLinesDiscountPercent2", 0.0) AS DOUBLE) AS "DISCOUNT_PERCENT2",
                            "AP_TERMS_LINES"."ApTermsLinesDiscountDayOfMonth3"                             AS "DISCOUNT_DAY_OF_MONTH3",
                            "AP_TERMS_LINES"."ApTermsLinesDiscountDays3"                                   AS "DISCOUNT_DAYS3",
                            "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward3"                          AS "DISCOUNT_MONTHS_FORWARD3",
                            CAST(COALESCE("AP_TERMS_LINES"."ApTermsLinesDiscountPercent3", 0.0) AS DOUBLE) AS "DISCOUNT_PERCENT3",
                            "AP_TERMS_LINES"."ApTermsLinesFixedDate"                                       AS "DUE_DATE",
                            "AP_TERMS_LINES"."ApTermsLinesDueDayOfMonth"                                   AS "DUE_DAY_OF_MONTH",
                            "AP_TERMS_LINES"."ApTermsLinesDueDays"                                         AS "DUE_DAYS",
                            "AP_TERMS_LINES"."ApTermsLinesDueMonthsForward"                                AS "DUE_MONTHS_FORWARD",
                            CASE
                                WHEN "AP_TERMS_LINES"."ApTermsLinesDueDays" IS NOT NULL THEN 1
                                WHEN "AP_TERMS_LINES"."ApTermsLinesFixedDate" IS NOT NULL THEN 2
                                WHEN "AP_TERMS_LINES"."ApTermsLinesDueDayOfMonth" IS NOT NULL
                                     AND "AP_TERMS_LINES"."ApTermsLinesDueMonthsForward" IS NOT NULL THEN 3
                                WHEN "AP_TERMS_LINES"."ApTermsLinesDueDayOfMonth" IS NULL
                                     AND "AP_TERMS_LINES"."ApTermsLinesDueDays" IS NULL
                                     AND "AP_TERMS_LINES"."ApTermsLinesDueMonthsForward" IS NULL THEN 4
                                ELSE 5 END                                                                 AS "DUEDATEMODE",
                            CASE
                                WHEN "AP_TERMS_LINES"."ApTermsLinesDiscountDays" IS NOT NULL THEN 1
                                WHEN "AP_TERMS_LINES"."ApTermsLinesDueDayOfMonth" IS NOT NULL
                                     AND "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward" IS NOT NULL THEN 3
                                WHEN "AP_TERMS_LINES"."ApTermsLinesDueDayOfMonth" IS NULL
                                     AND "AP_TERMS_LINES"."ApTermsLinesDueDays" IS NULL
                                     AND "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward" IS NULL THEN 4
                                ELSE 5 END                                                                 AS "DISCOUNTDATEMODE1",
                            CASE
                                WHEN "AP_TERMS_LINES"."ApTermsLinesDiscountDays2" IS NOT NULL THEN 1
                                WHEN "AP_TERMS_LINES"."ApTermsLinesDiscountDayOfMonth2" IS NOT NULL
                                     AND "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward2" IS NOT NULL THEN 3
                                WHEN
                                    "AP_TERMS_LINES"."ApTermsLinesDiscountDayOfMonth2" IS NULL
                                    AND "AP_TERMS_LINES"."ApTermsLinesDiscountDays2" IS NULL
                                    AND "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward2" IS NULL THEN 4
                                ELSE 5 END                                                                 AS "DISCOUNTDATEMODE2",
                            CASE
                                WHEN "AP_TERMS_LINES"."ApTermsLinesDiscountDays3" IS NOT NULL THEN 1
                                WHEN "AP_TERMS_LINES"."ApTermsLinesDiscountDayOfMonth3" IS NOT NULL
                                     AND "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward3" IS NOT NULL THEN 3
                                WHEN
                                    "AP_TERMS_LINES"."ApTermsLinesDiscountDayOfMonth3" IS NULL
                                    AND "AP_TERMS_LINES"."ApTermsLinesDiscountDays3" IS NULL
                                    AND "AP_TERMS_LINES"."ApTermsLinesDiscountMonthsForward3" IS NULL THEN 4
                                ELSE 5 END                                                                 AS "DISCOUNTDATEMODE3"
                     FROM "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_PaymentTermLineExtractPVO" AS "AP_TERMS_LINES"),
     "CTE_SUPPLIER_INFO" AS (SELECT "AP_SUPPLIER_SITES_ALL"."VendorSiteId" AS "VENDOR_SITE_ID",
                                    "AP_SUPPLIERS"."VendorId"              AS "VENDOR_ID",
                                    "AP_SUPPLIER_SITES_ALL"."TermsId"      AS "TERMS_ID"
                             FROM "FscmTopModelAM_PrcExtractAM_PozBiccExtractAM_SupplierSiteExtractPVO" AS "AP_SUPPLIER_SITES_ALL"
                                      LEFT JOIN "FscmTopModelAM_PrcPozPublicViewAM_SupplierPVO" AS "AP_SUPPLIERS"
                                                ON "AP_SUPPLIER_SITES_ALL"."VendorId" = "AP_SUPPLIERS"."VendorId"
                             WHERE "AP_SUPPLIERS"."VendorId" IS NOT NULL),
     "CTE_PORELATED" AS (SELECT "AP_INVOICE_LINES_ALL"."ApInvoiceLinesAllInvoiceId" AS "INVOICE_ID",
                                CASE
                                    WHEN COUNT("AP_INVOICE_LINES_ALL"."ApInvoiceLinesAllPoHeaderId") > 0 THEN 'Y'
                                    ELSE 'N' END                                    AS "PO_RELATED_FLAG"
                         FROM "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_InvoiceLineExtractPVO" AS "AP_INVOICE_LINES_ALL"
                         GROUP BY "AP_INVOICE_LINES_ALL"."ApInvoiceLinesAllInvoiceId")
SELECT <%=sourceSystem%>  || 'VendorAccountCreditItem_' || "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllInvoiceId" || '_'
       || "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllPaymentNum"                                 AS "ID",
       "LastValidation"."LastValidationTime"                                                           AS "CreationTime",
	<%=sourceSystem%>  || 'User_' || "LastValidation"."CREATED_BY"                                        AS "CreatedBy",
       CASE
           WHEN "AP_INVOICES_ALL"."ApInvoicesSource" = 'Manual Invoice Entry'
               THEN 'Manual'
           ELSE 'Automatic'
           END                                                                                         AS "CreationExecutionType",
	<%=sourceSystem%>  || 'VendorInvoice_' || "AP_INVOICES_ALL"."ApInvoicesInvoiceId"                     AS "VendorInvoice",
       "AP_INVOICES_ALL"."ApInvoicesInvoiceTypeLookupCode"                                             AS "DocumentType",
       "FND_LOOKUP_VALUES"."Description"                                                               AS "DocumentTypeText",
       CAST("AP_INVOICES_ALL"."ApInvoicesInvoiceDate" AS TIMESTAMP)                                    AS "DocumentDate",
       "AP_INVOICES_ALL"."ApInvoicesPaymentMethodCode"                                                 AS "PaymentMethod",
       "AP_INVOICES_ALL"."ApInvoicesInvoiceNum"                                                        AS "ReferenceDocumentNumber",
       CAST("AP_INVOICES_ALL"."ApInvoicesTermsDate" AS TIMESTAMP)                                      AS "BaseLineDate",
       CASE
           WHEN "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllDiscountDate" IS NULL THEN TIMESTAMPDIFF(DAY,
                                                                                                          "AP_INVOICES_ALL"."ApInvoicesTermsDate",
                                                                                                          "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllDueDate")
           ELSE COALESCE(TIMESTAMPDIFF(DAY, "AP_INVOICES_ALL"."ApInvoicesTermsDate",
                                       "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllDiscountDate"), 0)
           END
                                                                                                       AS "PaymentDays1",
       CASE
           WHEN "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllDiscountDate" IS NULL THEN 0
           WHEN "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllSecondDiscountDate" IS NULL THEN TIMESTAMPDIFF(DAY,
                                                                                                                "AP_INVOICES_ALL"."ApInvoicesTermsDate",
                                                                                                                "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllDueDate")
           ELSE
               TIMESTAMPDIFF(DAY, "AP_INVOICES_ALL"."ApInvoicesTermsDate",
                             "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllSecondDiscountDate") END AS "PaymentDays2",
       CASE
           WHEN "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllDiscountDate" IS NULL
                OR "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllSecondDiscountDate" IS NULL THEN 0
           ELSE TIMESTAMPDIFF(DAY, "AP_INVOICES_ALL"."ApInvoicesTermsDate",
                              "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllDueDate") END           AS "PaymentDays3",
       CASE
           WHEN COALESCE("AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllGrossAmount", 0) = 0
               THEN 0
           ELSE COALESCE(
                   "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllDiscountAmountAvailable"
                   / "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllGrossAmount"
                       * 100, 0)
           END                                                                                         AS "CashDiscountPercentage1",
       CASE
           WHEN COALESCE("AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllGrossAmount", 0) = 0
               THEN 0
           ELSE COALESCE(
                   "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllSecondDiscAmtAvailable"
                   / "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllGrossAmount"
                       * 100, 0)
           END                                                                                         AS "CashDiscountPercentage2",
       LEFT("AP_INVOICES_ALL"."ApInvoicesDescription", 180)                                            AS "ItemText",
       'VendorAccountCreditHead_' || "AP_INVOICES_ALL"."ApInvoicesInvoiceId"                           AS "VendorAccountHead",
	<%=sourceSystem%>  || 'Vendor_' || "AP_INVOICES_ALL"."ApInvoicesVendorSiteId"                         AS "Vendor",
       CAST(COALESCE("TERMS"."DISCOUNT_PERCENT1", 0.0) AS DOUBLE)                                      AS "VendorCashDiscountPercentage1",
       CAST(COALESCE("TERMS"."DISCOUNT_PERCENT2", 0.0) AS DOUBLE)                                      AS "VendorCashDiscountPercentage2",
       "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllInvCurrGrossAmount"                            AS "Amount",
       "AP_INVOICES_ALL"."ApInvoicesInvoiceCurrencyCode"                                               AS "Currency",
       COALESCE("AGG_INV_PAYM"."DISCOUNT_TAKEN", 0)                                                    AS "CashDiscountTakenAmount",
       COALESCE("AP_INVOICES_ALL"."ApInvoicesAmountApplicableToDiscount", 0)                           AS "CashDiscountEligibleAmount",
       CASE
           WHEN "AP_INVOICES_ALL"."ApInvoicesPaymentStatusFlag" = 'Y'
               THEN CAST("AGG_INV_PAYM"."PAYMENT_DATE" AS TIMESTAMP) END                               AS "ClearingDate",
       CAST("AP_INVOICES_ALL"."ApInvoicesTermsId" AS VARCHAR(255))                                     AS "PaymentTerms",
       CAST("AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllOrgId" AS VARCHAR)                        AS "CompanyCode",
       "HR_ALL_ORGANIZATION_UNITS"."FunBuPerfPEOName"                                                  AS "CompanyCodeText",
       CASE
           WHEN "TERMS"."DISCOUNTDATEMODE1" = 4
               THEN CASE
                        WHEN "TERMS"."DUEDATEMODE" = 1
                            THEN CAST("TERMS"."DUE_DAYS" AS INTEGER)
                        WHEN "TERMS"."DUEDATEMODE" = 2
                            THEN TIMESTAMPDIFF(DAY, CAST("AP_INVOICES_ALL"."ApInvoicesTermsDate" AS TIMESTAMP),
                                               CAST("TERMS"."DUE_DATE" AS TIMESTAMP))
                        WHEN "TERMS"."DUEDATEMODE" = 3
                            THEN TIMESTAMPDIFF(DAY, "AP_INVOICES_ALL"."ApInvoicesTermsDate",
                                               CASE
                                                   WHEN DAYOFMONTH(TIMESTAMPADD(DAY, -1,
                                                                                TIMESTAMPADD(MONTH,
                                                                                             CAST("TERMS"."DUE_MONTHS_FORWARD" AS INTEGER)
                                                                                             + 1,
                                                                                             CAST(YEAR("AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                                                  || '-' || MONTH(
                                                                                                          "AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                                                  || '-01' AS TIMESTAMP))))
                                                        <= CAST("TERMS"."DUE_DAY_OF_MONTH" AS INTEGER)
                                                       THEN TIMESTAMPADD(DAY, -1,
                                                                         TIMESTAMPADD(MONTH,
                                                                                      CAST("TERMS"."DUE_MONTHS_FORWARD" AS INTEGER)
                                                                                      + 1,
                                                                                      CAST(YEAR("AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                                           || '-' || MONTH(
                                                                                                   "AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                                           || '-01' AS TIMESTAMP)))
                                                   ELSE
                                                       TIMESTAMPADD(MONTH,
                                                                    CAST("TERMS"."DUE_MONTHS_FORWARD" AS INTEGER),
                                                                    CAST(YEAR("AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                         || '-'
                                                                         || MONTH(
                                                                                 "AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                         || '-'
                                                                         || CAST("TERMS"."DUE_DAY_OF_MONTH" AS INTEGER) AS TIMESTAMP))
                                                   END)
               END
           WHEN "TERMS"."DISCOUNTDATEMODE1" = 1
               THEN CAST("TERMS"."DISCOUNT_DAYS1" AS INTEGER)
           WHEN "TERMS"."DISCOUNTDATEMODE1" = 3
               THEN TIMESTAMPDIFF(DAY, "AP_INVOICES_ALL"."ApInvoicesTermsDate",
                                  CASE
                                      WHEN DAYOFMONTH(TIMESTAMPADD(DAY, -1,
                                                                   TIMESTAMPADD(MONTH,
                                                                                CAST("TERMS"."DISCOUNT_MONTHS_FORWARD1" AS INTEGER)
                                                                                + 1,
                                                                                CAST(YEAR("AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                                     || '-' || MONTH(
                                                                                             "AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                                     || '-01' AS TIMESTAMP))))
                                           <= CAST("TERMS"."DISCOUNT_DAY_OF_MONTH1" AS INTEGER)
                                          THEN TIMESTAMPADD(DAY, -1,
                                                            TIMESTAMPADD(MONTH,
                                                                         CAST("TERMS"."DISCOUNT_MONTHS_FORWARD1" AS INTEGER)
                                                                         + 1,
                                                                         CAST(YEAR("AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                              || '-'
                                                                              || MONTH(
                                                                                      "AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                              || '-01' AS TIMESTAMP)))
                                      ELSE
                                          TIMESTAMPADD(MONTH, CAST("TERMS"."DISCOUNT_MONTHS_FORWARD1" AS INTEGER),
                                                       CAST(YEAR("AP_INVOICES_ALL"."ApInvoicesTermsDate") || '-'
                                                            || MONTH(
                                                                    "AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                            || '-'
                                                            || CAST("TERMS"."DISCOUNT_DAY_OF_MONTH1" AS INTEGER) AS TIMESTAMP))
                                      END)
           ELSE 0
           END                                                                                         AS "VendorPaymentDays1",
       CASE
           WHEN "TERMS"."DISCOUNTDATEMODE1" = 4
               THEN 0
           WHEN "TERMS"."DISCOUNTDATEMODE2" = 4
               THEN CASE
                        WHEN "TERMS"."DUEDATEMODE" = 1
                            THEN CAST("TERMS"."DUE_DAYS" AS INTEGER)
                        WHEN "TERMS"."DUEDATEMODE" = 2
                            THEN TIMESTAMPDIFF(DAY, CAST("AP_INVOICES_ALL"."ApInvoicesTermsDate" AS TIMESTAMP),
                                               CAST("TERMS"."DUE_DATE" AS TIMESTAMP))
                        WHEN "TERMS"."DUEDATEMODE" = 3
                            THEN TIMESTAMPDIFF(DAY, "AP_INVOICES_ALL"."ApInvoicesTermsDate",
                                               CASE
                                                   WHEN DAYOFMONTH(TIMESTAMPADD(DAY, -1,
                                                                                TIMESTAMPADD(MONTH,
                                                                                             CAST("TERMS"."DUE_MONTHS_FORWARD" AS INTEGER)
                                                                                             + 1,
                                                                                             CAST(YEAR("AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                                                  || '-' || MONTH(
                                                                                                          "AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                                                  || '-01' AS TIMESTAMP))))
                                                        <= CAST("TERMS"."DUE_DAY_OF_MONTH" AS INTEGER)
                                                       THEN TIMESTAMPADD(DAY, -1,
                                                                         TIMESTAMPADD(MONTH,
                                                                                      CAST("TERMS"."DUE_MONTHS_FORWARD" AS INTEGER)
                                                                                      + 1,
                                                                                      CAST(YEAR("AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                                           || '-' || MONTH(
                                                                                                   "AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                                           || '-01' AS TIMESTAMP)))
                                                   ELSE
                                                       TIMESTAMPADD(MONTH,
                                                                    CAST("TERMS"."DUE_MONTHS_FORWARD" AS INTEGER),
                                                                    CAST(YEAR("AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                         || '-'
                                                                         || MONTH(
                                                                                 "AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                         || '-'
                                                                         || CAST("TERMS"."DUE_DAY_OF_MONTH" AS INTEGER) AS TIMESTAMP))
                                                   END)
                        WHEN "TERMS"."DUEDATEMODE" = 4
                            THEN 0
               END
           WHEN "TERMS"."DISCOUNTDATEMODE2" = 1
               THEN CAST("TERMS"."DISCOUNT_DAYS2" AS INTEGER)
           WHEN "TERMS"."DISCOUNTDATEMODE2" = 3
               THEN TIMESTAMPDIFF(DAY, "AP_INVOICES_ALL"."ApInvoicesTermsDate",
                                  CASE
                                      WHEN DAYOFMONTH(TIMESTAMPADD(DAY, -1,
                                                                   TIMESTAMPADD(MONTH,
                                                                                CAST("TERMS"."DISCOUNT_MONTHS_FORWARD2" AS INTEGER)
                                                                                + 1,
                                                                                CAST(YEAR("AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                                     || '-' || MONTH(
                                                                                             "AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                                     || '-01' AS TIMESTAMP))))
                                           <= CAST("TERMS"."DISCOUNT_DAY_OF_MONTH2" AS INTEGER)
                                          THEN TIMESTAMPADD(DAY, -1,
                                                            TIMESTAMPADD(MONTH,
                                                                         CAST("TERMS"."DISCOUNT_MONTHS_FORWARD2" AS INTEGER)
                                                                         + 1,
                                                                         CAST(YEAR("AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                              || '-'
                                                                              || MONTH(
                                                                                      "AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                              || '-01' AS TIMESTAMP)))
                                      ELSE
                                          TIMESTAMPADD(MONTH, CAST("TERMS"."DISCOUNT_MONTHS_FORWARD2" AS INTEGER),
                                                       CAST(YEAR("AP_INVOICES_ALL"."ApInvoicesTermsDate") || '-'
                                                            || MONTH(
                                                                    "AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                            || '-'
                                                            || CAST("TERMS"."DISCOUNT_DAY_OF_MONTH2" AS INTEGER) AS TIMESTAMP))
                                      END)
           ELSE 0
           END                                                                                         AS "VendorPaymentDays2",
       CASE
           WHEN "TERMS"."DISCOUNTDATEMODE1" = 4 OR "TERMS"."DISCOUNTDATEMODE2" = 4
               THEN 0
           WHEN "TERMS"."DUEDATEMODE" = 1
               THEN CAST("TERMS"."DUE_DAYS" AS INTEGER)
           WHEN "TERMS"."DUEDATEMODE" = 3
               THEN TIMESTAMPDIFF(DAY, "AP_INVOICES_ALL"."ApInvoicesTermsDate",
                                  CASE
                                      WHEN DAYOFMONTH(TIMESTAMPADD(DAY, -1,
                                                                   TIMESTAMPADD(MONTH,
                                                                                CAST("TERMS"."DUE_MONTHS_FORWARD" AS INTEGER)
                                                                                + 1,
                                                                                CAST(YEAR("AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                                     || '-' || MONTH(
                                                                                             "AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                                     || '-01' AS TIMESTAMP))))
                                           <= CAST("TERMS"."DUE_DAY_OF_MONTH" AS INTEGER)
                                          THEN TIMESTAMPADD(DAY, -1,
                                                            TIMESTAMPADD(MONTH,
                                                                         CAST("TERMS"."DUE_MONTHS_FORWARD" AS INTEGER)
                                                                         + 1,
                                                                         CAST(YEAR("AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                              || '-'
                                                                              || MONTH(
                                                                                      "AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                                              || '-01' AS TIMESTAMP)))
                                      ELSE
                                          TIMESTAMPADD(MONTH, CAST("TERMS"."DUE_MONTHS_FORWARD" AS INTEGER),
                                                       CAST(YEAR("AP_INVOICES_ALL"."ApInvoicesTermsDate") || '-'
                                                            || MONTH(
                                                                    "AP_INVOICES_ALL"."ApInvoicesTermsDate")
                                                            || '-'
                                                            || CAST("TERMS"."DUE_DAY_OF_MONTH" AS INTEGER) AS TIMESTAMP))
                                      END)
           WHEN "TERMS"."DUEDATEMODE" = 4
               THEN 0
           ELSE 0
           END                                                                                         AS "VendorPaymentDays3",
       'Oracle Fusion'                                                                                 AS "SourceSystemType",
	<%=sourceSystem%>  || ''                                                                              AS "SourceSystemInstance",
       "PERIOD_LOOKUP"."PERIOD_YEAR"                                                                   AS "FiscalYear",
       CAST("AP_INVOICES_ALL"."ApInvoicesInvoiceNum" AS VARCHAR(255))                                  AS "SystemAccountingDocumentNumber",
       CAST("AP_INVOICES_ALL"."ApInvoicesInvoiceId" AS VARCHAR(255))                                   AS "DatabaseAccountingDocumentNumber",
       CASE
           WHEN "AP_INVOICES_ALL"."ApInvoicesCancelledDate" IS NOT NULL
               THEN 'Reversed Document'
           END                                                                                         AS "ReversalIndicator",
       CAST("AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllPaymentNum" AS VARCHAR(255))              AS "SystemAccountingDocumentItemNumber",
       CAST("AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllPaymentNum" AS VARCHAR(255))              AS "DatabaseAccountingDocumentItemNumber",
       'InvoiceItem'                                                                                   AS "VendorAccountTransactionType",
       COALESCE(CAST("AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllSecondDiscountDate" AS TIMESTAMP),
                CAST("AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllDiscountDate" AS TIMESTAMP))     AS "CashDiscountDueDate",
       CAST("AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllDueDate" AS TIMESTAMP)                    AS "DueDate",
       CASE
           WHEN "PO_RELATED"."PO_RELATED_FLAG" = 'Y' THEN TRUE
           ELSE FALSE
           END                                                                                         AS "PurchaseOrderRelated",
	<%=sourceSystem%>  || NULL                                                                            AS "Material",
	<%=sourceSystem%>  || 'VendorMasterCompanyCode_' || "AP_INVOICES_ALL"."ApInvoicesVendorSiteId"        AS "VendorMasterCompanyCode"
FROM "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_InvoicePaymentScheduleExtractPVO" AS "AP_PAYMENT_SCHEDULES_ALL"
         LEFT JOIN "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_InvoiceHeaderExtractPVO" AS "AP_INVOICES_ALL"
                   ON "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllInvoiceId"
                      = "AP_INVOICES_ALL"."ApInvoicesInvoiceId"
         LEFT JOIN "CTE_AGG_INV_PAYM" AS "AGG_INV_PAYM"
                   ON "AP_INVOICES_ALL"."ApInvoicesInvoiceId" = "AGG_INV_PAYM"."INVOICE_ID"
                       AND "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllPaymentNum" = "AGG_INV_PAYM"."PAYMENT_NUM"
         LEFT JOIN "CTE_PORELATED" AS "PO_RELATED"
                   ON "AP_INVOICES_ALL"."ApInvoicesInvoiceId" = "PO_RELATED"."INVOICE_ID"
         LEFT JOIN "FscmTopModelAM_FinExtractAM_FunBiccExtractAM_BusinessUnitExtractPVO" AS "HR_ALL_ORGANIZATION_UNITS"
                   ON "AP_INVOICES_ALL"."ApInvoicesOrgId" = "HR_ALL_ORGANIZATION_UNITS"."FunBuPerfPEOBusinessUnitId"
         LEFT JOIN "FscmTopModelAM_FinExtractAM_AnalyticsExtractServiceAM_LookupValuesTLExtractPVO" AS "FND_LOOKUP_VALUES"
                   ON "AP_INVOICES_ALL"."ApInvoicesInvoiceTypeLookupCode" = "FND_LOOKUP_VALUES"."LookupCode"
                       AND "FND_LOOKUP_VALUES"."LookupType" = 'INVOICE TYPE'
                       AND "FND_LOOKUP_VALUES"."Language" = <%=LanguageKey%> 
                       AND "FND_LOOKUP_VALUES"."ViewApplicationId" = '200'
         LEFT JOIN "CTE_PERIOD_LOOKUP" AS "PERIOD_LOOKUP"
                   ON "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllInvoiceId" = "PERIOD_LOOKUP"."INVOICE_ID"
         LEFT JOIN "CTE_SUPPLIER_INFO" AS "SUPPLIER_INFO"
                   ON "AP_INVOICES_ALL"."ApInvoicesVendorId" = "SUPPLIER_INFO"."VENDOR_ID"
                       AND "AP_INVOICES_ALL"."ApInvoicesVendorSiteId" = "SUPPLIER_INFO"."VENDOR_SITE_ID"
         LEFT JOIN "CTE_TERMS" AS "TERMS"
                   ON "SUPPLIER_INFO"."TERMS_ID" = "TERMS"."TERM_ID"
                       AND "AP_PAYMENT_SCHEDULES_ALL"."ApPaymentSchedulesAllPaymentNum" = "TERMS"."SEQUENCE_NUM"
         LEFT JOIN "CTE_LastValidation" AS "LastValidation"
                   ON "AP_INVOICES_ALL"."ApInvoicesInvoiceId" = "LastValidation"."INVOICE_ID"
         LEFT JOIN "CTE_FullValidation" AS "FullValidation"
                   ON "AP_INVOICES_ALL"."ApInvoicesInvoiceId" = "FullValidation"."INVOICE_ID"
WHERE "AP_INVOICES_ALL"."ApInvoicesInvoiceTypeLookupCode" = 'STANDARD'
  AND "LastValidation"."INVOICE_ID" IS NOT NULL
  AND "FullValidation"."INVOICE_ID" IS NOT NULL

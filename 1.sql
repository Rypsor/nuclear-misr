WITH "CTE_GL_PERIOD_YEAR" AS (SELECT DISTINCT "GL_PERIOD_STATUSES"."GlPeriodStatusesPeriodName"   AS "PERIOD_NAME",
                                              "GL_PERIOD_STATUSES"."GlPeriodStatusesPeriodYear"   AS "PERIOD_YEAR",
                                              "GL_PERIOD_STATUSES"."GlPeriodStatusesSetOfBooksId" AS "SET_OF_BOOKS_ID"
                              FROM "FscmTopModelAM_FinExtractAM_GlBiccExtractAM_PeriodStatusExtractPVO" AS "GL_PERIOD_STATUSES"),
     "CTE_Aggregate_PeriodYear" AS (SELECT "AP_INVOICE_PAYMENTS_ALL"."ApInvoicePaymentsAllCheckId" AS "CHECK_ID",
                                           MAX("PeriodNameLookup"."PERIOD_YEAR")                   AS "PERIOD_YEAR"
                                    FROM "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_PaidDisbursementScheduleExtractPVO" AS "AP_INVOICE_PAYMENTS_ALL"
                                             LEFT JOIN "CTE_GL_PERIOD_YEAR" AS "PeriodNameLookup"
                                                       ON "AP_INVOICE_PAYMENTS_ALL"."ApInvoicePaymentsAllPeriodName"
                                                          = "PeriodNameLookup"."PERIOD_NAME"
                                                           AND
                                                          "AP_INVOICE_PAYMENTS_ALL"."ApInvoicePaymentsAllSetOfBooksId"
                                                          = "PeriodNameLookup"."SET_OF_BOOKS_ID"
                                    WHERE "AP_INVOICE_PAYMENTS_ALL"."ApInvoicePaymentsAllAmount" > 0
                                    GROUP BY "AP_INVOICE_PAYMENTS_ALL"."ApInvoicePaymentsAllCheckId")
SELECT <%=sourceSystem%>  || 'VendorAccountCreditItem_' || "AP_CHECKS_ALL"."ApChecksAllCheckId" AS "ID",
       CAST("AP_CHECKS_ALL"."ApChecksAllVoidDate" AS TIMESTAMP)                                 AS "CreationTime",
	<%=sourceSystem%>  || 'User_' || "AP_CHECKS_ALL"."ApChecksAllCreatedBy"                        AS "CreatedBy",
       CASE
           WHEN "AP_CHECKS_ALL"."ApChecksAllPaymentTypeFlag" = 'A'
               THEN 'Automatic'
           ELSE 'Manual'
           END                                                                                  AS "CreationExecutionType",
	<%=sourceSystem%>  || NULL                                                                     AS "VendorInvoice",
       "FND_LOOKUP_VALUES"."Meaning"                                                            AS "DocumentType",
       "FND_LOOKUP_VALUES"."Description"                                                        AS "DocumentTypeText",
       CAST("AP_CHECKS_ALL"."ApChecksAllCheckDate" AS TIMESTAMP)                                AS "DocumentDate",
       "AP_CHECKS_ALL"."ApChecksAllPaymentMethodCode"                                           AS "PaymentMethod",
       CAST("AP_CHECKS_ALL"."ApChecksAllCheckNumber" AS VARCHAR(255))                           AS "ReferenceDocumentNumber",
       NULL                                                                                     AS "BaseLineDate",
       CAST(0 AS BIGINT)                                                                        AS "PaymentDays1",
       CAST(0 AS BIGINT)                                                                        AS "PaymentDays2",
       CAST(0 AS BIGINT)                                                                        AS "PaymentDays3",
       CAST(0.0 AS DOUBLE)                                                                      AS "CashDiscountPercentage1",
       CAST(0.0 AS DOUBLE)                                                                      AS "CashDiscountPercentage2",
       LEFT("AP_CHECKS_ALL"."ApChecksAllDescription", 180)                                      AS "ItemText",
       'VendorAccountCreditHead_' || "AP_CHECKS_ALL"."ApChecksAllCheckId"                       AS "VendorAccountHead",
	<%=sourceSystem%>  || 'Vendor_' || "AP_CHECKS_ALL"."ApChecksAllVendorSiteId"                   AS "Vendor",
       CAST(0.0 AS DOUBLE)                                                                      AS "VendorCashDiscountPercentage1",
       CAST(0.0 AS DOUBLE)                                                                      AS "VendorCashDiscountPercentage2",
       ABS("AP_CHECKS_ALL"."ApChecksAllAmount")                                                 AS "Amount",
       "AP_CHECKS_ALL"."ApChecksAllCurrencyCode"                                                AS "Currency",
       CAST(0 AS BIGINT)                                                                        AS "CashDiscountTakenAmount",
       CAST(0 AS BIGINT)                                                                        AS "CashDiscountEligibleAmount",
       CAST("AP_CHECKS_ALL"."ApChecksAllClearedDate" AS TIMESTAMP)                              AS "ClearingDate",
       NULL                                                                                     AS "PaymentTerms",
       CAST("AP_CHECKS_ALL"."ApChecksAllOrgId" AS VARCHAR(255))                                 AS "CompanyCode",
       "HR_ALL_ORGANIZATION_UNITS"."FunBuPerfPEOName"                                           AS "CompanyCodeText",
       CAST(0 AS BIGINT)                                                                        AS "VendorPaymentDays1",
       CAST(0 AS BIGINT)                                                                        AS "VendorPaymentDays2",
       CAST(0 AS BIGINT)                                                                        AS "VendorPaymentDays3",
       'Oracle Fusion'                                                                          AS "SourceSystemType",
	<%=sourceSystem%>  || ''                                                                       AS "SourceSystemInstance",
       "Aggregate_PeriodYear"."PERIOD_YEAR"                                                     AS "FiscalYear",
       CAST("AP_CHECKS_ALL"."ApChecksAllCheckNumber" AS VARCHAR(255))                           AS "SystemAccountingDocumentNumber",
       CAST("AP_CHECKS_ALL"."ApChecksAllCheckId" AS VARCHAR(255))                               AS "DatabaseAccountingDocumentNumber",
       'Reversal Document'                                                                      AS "ReversalIndicator",
       NULL                                                                                     AS "SystemAccountingDocumentItemNumber",
       NULL                                                                                     AS "DatabaseAccountingDocumentItemNumber",
       'ReversePayment'                                                                         AS "VendorAccountTransactionType",
       NULL                                                                                     AS "CashDiscountDueDate",
       NULL                                                                                     AS "DueDate",
       FALSE                                                                                    AS "PurchaseOrderRelated",
	<%=sourceSystem%>  || NULL                                                                     AS "Material",
	<%=sourceSystem%>  || 'VendorMasterCompanyCode_' || "AP_CHECKS_ALL"."ApChecksAllVendorSiteId"  AS "VendorMasterCompanyCode"
FROM "FscmTopModelAM_FinExtractAM_ApBiccExtractAM_DisbursementHeaderExtractPVO" AS "AP_CHECKS_ALL"
         LEFT JOIN "CTE_Aggregate_PeriodYear" AS "Aggregate_PeriodYear"
                   ON "AP_CHECKS_ALL"."ApChecksAllCheckId" = "Aggregate_PeriodYear"."CHECK_ID"
         LEFT JOIN "FscmTopModelAM_FinExtractAM_FunBiccExtractAM_BusinessUnitExtractPVO" AS "HR_ALL_ORGANIZATION_UNITS"
                   ON "AP_CHECKS_ALL"."ApChecksAllOrgId" = "HR_ALL_ORGANIZATION_UNITS"."FunBuPerfPEOBusinessUnitId"
         LEFT JOIN "FscmTopModelAM_FinExtractAM_AnalyticsExtractServiceAM_LookupValuesTLExtractPVO" AS "FND_LOOKUP_VALUES"
                   ON "AP_CHECKS_ALL"."ApChecksAllPaymentTypeFlag" = "FND_LOOKUP_VALUES"."LookupCode"
                       AND "FND_LOOKUP_VALUES"."LookupType" = 'PAYMENT TYPE'
                       AND "FND_LOOKUP_VALUES"."Language" = <%=LanguageKey%> 
                       AND "FND_LOOKUP_VALUES"."ViewApplicationId" = '200'
WHERE "AP_CHECKS_ALL"."ApChecksAllVoidDate" IS NOT NULL
  AND "AP_CHECKS_ALL"."ApChecksAllPaymentTypeFlag" <> 'R'

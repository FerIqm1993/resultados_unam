/*************************************************************************
* ADOBE CONFIDENTIAL
* ___________________
*
*  Copyright 2015 Adobe Systems Incorporated
*  All Rights Reserved.
*
* NOTICE:  All information contained herein is, and remains
* the property of Adobe Systems Incorporated and its suppliers,
* if any.  The intellectual and technical concepts contained
* herein are proprietary to Adobe Systems Incorporated and its
* suppliers and are protected by all applicable intellectual property laws,
* including trade secret and or copyright laws.
* Dissemination of this information or reproduction of this material
* is strictly forbidden unless prior written permission is obtained
* from Adobe Systems Incorporated.
**************************************************************************/
export const openWebpageToPdfViewerForTab=(e,o)=>{if(!e||!e.id||!o)return;const t=(e.title||"webpage").replace(/[<>:"/\\|?*\x00-\x1F]/g,"").replace(/\s+/g," ").trim().substring(0,200)||"webpage",n=t.endsWith(".html")?t:`${t}.html`,r=`https://convert-pdf-webpage/?htmlToPdfSessionId=${encodeURIComponent(o)}`,p=`${chrome.runtime.getURL("viewer.html")}?pdfurl=${encodeURIComponent(`${r}&acrobatPromotionSource=webpage_chrome-convert_to_pdf`)}&pdffilename=${encodeURIComponent(n)}&acrobatPromotionWorkflow=${encodeURIComponent("html-to-pdf")}`;chrome.tabs.create({url:p,active:!0})};
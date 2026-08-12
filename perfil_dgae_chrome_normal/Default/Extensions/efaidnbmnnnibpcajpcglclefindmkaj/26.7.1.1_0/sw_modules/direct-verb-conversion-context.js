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
const e=new Map;function t(){const t=Date.now();e.forEach((n,r)=>{t-n.createdAt>18e5&&e.delete(r)})}export function createHtmlToPdfSession(n={}){const{sourceTabId:r,sourceTabUrl:o,frameId:c,targetSectionId:s}=n;if(!Number.isInteger(r))return null;if(t(),e.size>=200){const t=e.keys().next().value;void 0!==t&&e.delete(t)}const u=crypto.randomUUID();return e.set(u,{sourceTabId:r,sourceTabUrl:o||null,frameId:Number.isInteger(c)?c:null,targetSectionId:s||null,createdAt:Date.now()}),u}export function getHtmlToPdfSession(n){return n?(t(),e.get(n)||null):null}export function deleteHtmlToPdfSessionsForSourceTab(t){Number.isInteger(t)&&e.forEach((n,r)=>{n.sourceTabId===t&&e.delete(r)})}
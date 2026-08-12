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
import{dcLocalStorage as t}from"../../common/local-storage.js";import{SIDE_PANEL_HASH_ROUTES as e}from"../../common/constant.js";import{util as o}from"../../browser/js/content-util.js";import{checkCdnConnectivity as n}from"../../common/util.js";import{createSendAnalytics as r,getSidePanelTabId as m,isHomeShellRoute as a}from"./sidePanelUtil.js";import{fetchAndSendHtmlContent as i}from"./htmlContentFetcher.js";import{getGenAiPrerenderState as s,shouldShowTrefoilLoader as d,showTrefoilLoader as l}from"./loaderUIHelper.js";import{Cdn as c}from"./cdn.js";import{initHomeMode as p}from"./home.js";import{initOfflineMode as f}from"./offline.js";import{registerHostedShellListeners as I}from"./shell-listeners.js";const h=Date.now();await t.init();const E=t.getItem("isSidePanelHomeEnabled");let u=t.getItem("touchpoint");t.removeItem("touchpoint");let w=t.getItem("hashRoute");t.removeItem("hashRoute"),u||(u="ExtensionAction",w=e.HOME),E||(w=e.SIDE_PANEL);const S=a(w),j=document.getElementById("tooltipTextEnabled");E&&S&&j&&(j.id="tooltipTextEnabledHome"),o.translateElementsByAppLocale(".translate");const b=await s(w,u);d(b)&&l(),b?.showPreRendered&&(t=>{const e=document.createElement("iframe");e.id="sidepanelPreRendered",e.title="Adobe Chatbot",e.srcdoc=t,document.body.appendChild(e)})(b.anonGenAISSRHtml);const A=t.getItem("sidepanelUrl");if(A){await n(A)?S?await p(h,w,u):await async function(t,o,n){const a=m(),s=r(a);s(`DCBrowserExt:SidePanel:Opened:${o||"Unspecified"}`);const d=new c({initTimeStamp:t,hostedHashRoute:e.SIDE_PANEL,touchpoint:o,anonGenAISSRHtml:n?.anonGenAISSRHtml,onIframeLoad:()=>s(`DCBrowserExt:SidePanel:IframeLoaded:${o}`),onIframeError:()=>s(`DCBrowserExt:SidePanel:IframeLoadError:${o}`)});I({cdn:d,sendAnalytics:s,tabId:a,touchpoint:o}),await i({cdn:d,tabId:d.tabId,touchpoint:o})}(h,u,b):f(h)}
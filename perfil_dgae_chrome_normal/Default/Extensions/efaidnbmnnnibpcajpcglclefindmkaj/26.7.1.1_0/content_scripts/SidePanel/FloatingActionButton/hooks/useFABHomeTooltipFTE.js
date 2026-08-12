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
import{useState,useEffect,useRef}from"react";export const FAB_HOME_TOOLTIP_FTE_SHOWN_KEY="fabHomeTooltipFTEShown";let isFTESessionActiveForPage=!1;export const useFABHomeTooltipFTE=()=>{const[e,o]=useState(!1),t=useRef(isFTESessionActiveForPage),i=useRef(null);return useEffect(()=>((async()=>{await initDcLocalStorage(),window.dcLocalStorage?.getItem("isSidePanelHomeEnabled")&&(window.dcLocalStorage?.getItem("fabHomeTooltipFTEShown")||(window.dcLocalStorage?.setItem("fabHomeTooltipFTEShown",!0),isFTESessionActiveForPage=!0,t.current=!0,o(!0),i.current=setTimeout(()=>{o(!1),i.current=null},5e3)))})(),()=>{i.current&&clearTimeout(i.current)}),[]),{showTooltip:e,isFTESessionActiveRef:t}};
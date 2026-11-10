const aliases=new Set(['analytics','reports','analytics-reports']);
export function isAnalyticsLocation(location:{hash:string;pathname:string}){
 const hash=location.hash.replace(/^#\/?/,'').split('?')[0].replace(/\/$/,'');
 return aliases.has(hash)||(!hash&&aliases.has(location.pathname.replace(/^\//,'').replace(/\/$/,'')));
}
export function analyticsCanonicalUrl(location:{hash:string;pathname:string;search:string}){
 const path=aliases.has(location.pathname.replace(/^\//,'').replace(/\/$/,''))?'/analytics-reports':location.pathname;
 return path+location.search+'#/analytics-reports';
}
export function operatorBaseUrl(location:{pathname:string;search:string}){
 return (aliases.has(location.pathname.replace(/^\//,'').replace(/\/$/,''))?'/':location.pathname)+location.search;
}

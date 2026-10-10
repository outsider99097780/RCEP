
function ingest(s){
 let pages=load("mys_pages")||{};
 for(const block of String(s).split("--------------------------------------------------------------------------------")){
  const u=block.match(/\((https:\/\/my\.priceshop\.com\/product\/[^)\s]+)\)/);
  const meta=block.match(/cite([^]+) \[wordlim:/);
  const total=block.match(/Total lines: (\d+)/);
  if(!u||!meta||!total)continue;
  const url=u[1].replace(/\?.*/,""), key=url.split("/").pop();
  const ref=meta[1],age=(block.match(/Crawled: ([^;]+);/)||[])[1]||"not_reported";
  let p=pages[key];
  if(!p||p.total_lines!==Number(total[1])||p.crawl_age_raw!==age){p={url,ref,title: block.split("\n")[0].split(" Harga")[0],crawl_age_raw:age,total_lines:Number(total[1]),lines:{},parts:[]};}
  for(const m of block.matchAll(/L(\d+): ([\s\S]*?)(?=L\d+: |$)/g))p.lines[m[1]]=m[2].trim();
  p.parts.push({ref,start:Math.min(...Object.keys(p.lines).map(Number)),end:Math.max(...Object.keys(p.lines).map(Number)),retrieved_at:new Date().toISOString()});
  pages[key]=p;
 }
 store("mys_pages",pages);
 return Object.values(pages).map(p=>({slug:p.url.split("/").pop(),ref:p.ref,total:p.total_lines,covered:Object.keys(p.lines).length,next_missing:Array.from({length:p.total_lines},(_,i)=>i).find(i=>!(i in p.lines))}));
}
function clean(s){return s.replace(/\[Image \d+: ([^\]]+)\]/g,"Image: $1 ").replace(/\[Image \d+\]/g,"Image ").replace(/cite\d+†([^†]+)(?:†[^]*)?/g,"$1").trim();}
function facts(p){
 const pairs=Object.entries(p.lines).sort((a,b)=>+a[0]-+b[0]).map(([n,t])=>({n:+n,t:clean(t)}));
 let i=pairs.findIndex(x=>/^# /.test(x.t));
 const header=pairs.slice(i);const h=header.find(x=>/^# /.test(x.t));const title=h?h.t.slice(2):p.title;
 const price=header.find(x=>/^RM[\d,.]+(?: - RM[\d,.]+)?$/.test(x.t));
 const sellers=header.find(x=>/^From \d+ sellers?$/.test(x.t));
 const start=header.findIndex(x=>x.t==="Price comparison");
 const specStart=header.findIndex(x=>/^###### /.test(x.t));
 const section=header.slice(start>=0?start:10,specStart>=0?specStart:undefined);
 let imageParent="",name="",loc="",group="",declared="",nameLine=null,update="",promos=[],ofs=[];
 for(let j=0;j<section.length;j++){
  let x=section[j],t=x.t;
  const img=t.match(/Image: (.*?)(?=Image|$)/);
  if(img&& !/^(brand-new|PriceCare|Price Shop Malaysia)$/i.test(img[1].trim())){
   imageParent=img[1].trim(); name="";loc="";update="";promos=[];nameLine=null;
   const nxt=section.slice(j+1).find(a=>a.t&&!/^Image/.test(a.t)&&!/^Order now|^Buy online/.test(a.t));
   if(nxt){name=nxt.t;nameLine=nxt.n;}
  }
  if(/^\d+ locations$/.test(t)){group=imageParent;declared=t.match(/\d+/)[0];}
  if(/, (Selangor|Wp Kuala Lumpur|Johor|Penang|Kedah|Perak|Negeri Sembilan|Melaka|Sabah|Sarawak|Pahang|Kelantan|Terengganu|Perlis|Putrajaya|Labuan)/i.test(t)&&t.length<100)loc=t;
  if(/Updated as of/i.test(t))update=t;
  if(/Normal price|\bRM\d+ off|voucher|coupon|member|cashback/i.test(t)&&t.length<150)promos.push(t);
  if(/^RM[\d,.]+$/.test(t)){
    if(name&&name.length<100&&!/^Image|^Cheapest/.test(name)){
     ofs.push({retailer_name_raw:name,merchant_group_raw:group===imageParent?group:imageParent,merchant_group_locations_raw:group===imageParent?declared:"",location_raw:loc,price_raw:t,price_line:x.n,name_line:nameLine,quote_updated_raw:update,promotion_notes_raw:[...new Set(promos)]});
    }
  }
 }
 const specs={};let sec="";
 const rest=specStart>=0?header.slice(specStart):[];
 for(let j=0;j<rest.length;j++){
  const t=rest[j].t;
  if(/^\* |^©|^All Categories|^English/.test(t))break;
  if(/^###### /.test(t)){sec=t.slice(7);continue;}
  if(!t||/^Image|^©|^Share|^Previous|^Next/.test(t))continue;
  const nxt=rest.slice(j+1).find(x=>x.t);
  if(nxt&&!/^###### |^Image|^©/.test(nxt.t)){specs[t]={value_raw:nxt.t,section:sec,line:rest[j].n,value_line:nxt.n};j=rest.indexOf(nxt);}
 }
 return {source_site:"PriceShop",source_provider:"Price Guide Sdn Bhd",country_code:"MYS",currency:"MYR",source_product_id:p.url.split("/").pop(),url:p.url,title_raw:title,source_cache_age_raw:p.crawl_age_raw,accessed_at:new Date().toISOString(),http_status:null,access_method:"public_web_reader_cached_page",full_reader_document_read:Object.keys(p.lines).length===p.total_lines,reader_total_lines:p.total_lines,reader_captured_lines:Object.keys(p.lines).length,summary_price_raw:price?price.t:"",declared_seller_count_raw:sellers?sellers.t:"",specifications_raw:specs,offers_raw:ofs,reader_reference:p.ref,cache_is_not_live_stock_check:true,raw_snapshot_type:"selected_public_fact_fields_not_full_HTML"};
}


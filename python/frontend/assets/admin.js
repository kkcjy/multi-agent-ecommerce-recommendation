const ADMIN_KEY_STORAGE="novacartAdminApiKey";
const ADMIN_NAME_STORAGE="novacartAdminName";
const $=(id)=>document.getElementById(id);
const els={
  loginPanel:$("adminLoginPanel"),dashboard:$("adminDashboard"),loginForm:$("adminLoginForm"),account:$("adminAccount"),apiKey:$("adminApiKey"),loginBtn:$("adminLoginBtn"),loginState:$("adminLoginState"),adminName:$("adminName"),logout:$("adminLogout"),refreshAll:$("refreshAll"),
  expBox:$("experimentsContainer"),metricBox:$("metricsContainer"),behaviorBox:$("behaviorContainer"),catalogBox:$("catalogContainer"),expState:$("experimentsState"),metricState:$("metricsState"),behaviorState:$("behaviorState"),catalogState:$("catalogState"),
  reloadExp:$("reloadExperiments"),reloadMetric:$("reloadMetrics"),reloadBehavior:$("reloadBehavior"),reloadCatalog:$("reloadCatalog"),outcomeForm:$("outcomeForm"),outcomeState:$("outcomeState"),outcomeBtn:$("outcomeSubmitBtn"),
  experimentId:$("experimentId"),groupName:$("groupName"),isSuccess:$("isSuccess"),statExp:$("statExperiments"),statAgents:$("statAgents"),statOrders:$("statOrders"),statFavorites:$("statFavorites"),statCatalogProducts:$("statCatalogProducts")
};
let adminKey=localStorage.getItem(ADMIN_KEY_STORAGE)||"";
let loading={exp:false,metric:false,behavior:false,catalog:false};
function headers(){return {"X-API-Key":adminKey};}
function getAdminAuth(){try{return JSON.parse(localStorage.getItem("novacartAuth")||"null");}catch(e){return null;}}
function hasUnifiedAdminLogin(){const auth=getAdminAuth();return !!auth&&auth.role==="admin"&&!!adminKey;}
function showDashboard(ok){els.loginPanel.hidden=true;els.dashboard.hidden=!ok;if(ok)els.adminName.textContent=localStorage.getItem(ADMIN_NAME_STORAGE)||"admin";}
function safe(v){return v===null||v===undefined?"-":String(v);}
function rate(s,f){const t=s+f;return t?((s/t)*100).toFixed(1)+"%":"0.0%";}
function money(n){return "¥"+Number(n||0).toLocaleString("zh-CN");}
function parseJson(value,fallback){try{return JSON.parse(value||"");}catch(e){return fallback;}}
function storageItems(prefix){const items=[];for(let i=0;i<localStorage.length;i+=1){const key=localStorage.key(i);if(key&&key.startsWith(prefix)){items.push({key,value:parseJson(localStorage.getItem(key),[])});}}return items;}
function currentAuth(){return parseJson(localStorage.getItem("novacartAuth"),null);}

function renderExperiments(data){
  const ids=Object.keys(data||{});els.statExp.textContent=String(ids.length);
  if(!ids.length){els.expBox.innerHTML='<div class="empty-state">暂无实验数据。</div>';return;}
  els.expBox.innerHTML=ids.map(id=>{
    const exp=data[id]||{};const groups=Array.isArray(exp.groups)?exp.groups:[];
    const rows=groups.map(g=>{const s=Number(g.successes||0),f=Number(g.failures||0);return `<tr><td>${AppUI.escapeHtml(safe(g.name))}</td><td>${AppUI.escapeHtml(safe(g.weight))}</td><td>${s} / ${f}</td><td>${rate(s,f)}</td><td class="mono">${AppUI.escapeHtml(JSON.stringify(g.config||{}))}</td></tr>`;}).join("");
    return `<article class="info-card experiment-card"><div class="info-title-row"><div class="info-title">${AppUI.escapeHtml(id)}</div><span class="tag ${exp.enabled?"tag-ok":"tag-muted"}">${exp.enabled?"启用":"停用"}</span></div><div class="subtle-text">${AppUI.escapeHtml(exp.name||"未命名实验")}</div><div class="table-wrap"><table class="group-table"><thead><tr><th>分组</th><th>权重</th><th>成功/失败</th><th>成功率</th><th>配置</th></tr></thead><tbody>${rows}</tbody></table></div></article>`;
  }).join("");
}

function renderMetrics(data){
  const agents=(data&&data.agents)||{};const names=Object.keys(agents);els.statAgents.textContent=String(names.length);
  if(!names.length){els.metricBox.innerHTML='<div class="empty-state">暂无 Agent 指标。先到用户中心触发一次推荐请求，再回来刷新。</div>';return;}
  const agentHtml=names.map(name=>{const m=agents[name]||{};const errors=Array.isArray(m.recent_errors)?m.recent_errors:[];return `<article class="info-card"><div class="info-title">${AppUI.escapeHtml(name)}</div><div class="kv"><strong>调用次数</strong><span>${AppUI.escapeHtml(safe(m.call_count))}</span></div><div class="kv"><strong>成功率</strong><span>${AppUI.escapeHtml(safe(m.success_rate))}</span></div><div class="kv"><strong>平均延迟(ms)</strong><span>${AppUI.escapeHtml(safe(m.avg_latency_ms))}</span></div><div class="subtle-text">${errors.length?"最近错误："+AppUI.escapeHtml(errors.join(" | ")):"最近无错误。"}</div></article>`;}).join("");
  const biz=(data&&data.business)||{};const bizKeys=Object.keys(biz);
  const bizHtml=bizKeys.length?`<article class="info-card"><div class="info-title">业务指标</div>${bizKeys.map(k=>`<div class="kv"><strong>${AppUI.escapeHtml(k)}</strong><span>${AppUI.escapeHtml(safe(biz[k]&&biz[k].count))}</span></div>`).join("")}</article>`:'<article class="info-card"><div class="info-title">业务指标</div><div class="subtle-text">暂无业务事件。</div></article>';
  els.metricBox.innerHTML=agentHtml+bizHtml;
}

function collectBehaviorStats(){
  const auth=currentAuth();
  const carts=storageItems("cart_");
  const orders=storageItems("orders_");
  const cartItems=carts.reduce((sum,item)=>sum+(Array.isArray(item.value)?item.value.reduce((s,p)=>s+Number(p.quantity||1),0):0),0);
  const orderCount=orders.reduce((sum,item)=>sum+(Array.isArray(item.value)?item.value.length:0),0);
  const orderAmount=orders.reduce((sum,item)=>sum+(Array.isArray(item.value)?item.value.reduce((s,o)=>s+Number(o.total_amount||0),0):0),0);
  const favoriteBuckets=storageItems("favorites_");
  
  const favorites=favoriteBuckets.flatMap(item=>Array.isArray(item.value)?item.value.map(v=>({...v,userId:item.key.replace("favorites_","")})):[]);
  const searchBuckets=storageItems("recentSearches_");
  
  const searches=searchBuckets.flatMap(item=>Array.isArray(item.value)?item.value.map(v=>({term:v,userId:item.key.replace("recentSearches_","")})):[]);
  const viewBuckets=storageItems("viewHistory_");
  
  const views=viewBuckets.flatMap(item=>Array.isArray(item.value)?item.value.map(v=>({...v,userId:item.key.replace("viewHistory_","")})):[]);
  const recBuckets=storageItems("recommendHistory_");
  
  const recHistory=recBuckets.flatMap(item=>Array.isArray(item.value)?item.value.map(v=>({...v,userId:item.key.replace("recommendHistory_","")})):[]);
  return {auth,carts,orders,cartItems,orderCount,orderAmount,favorites,searches,views,recHistory};
}
function renderBehavior(){
  const s=collectBehaviorStats();
  els.statOrders.textContent=String(s.orderCount);
  els.statFavorites.textContent=String(Array.isArray(s.favorites)?s.favorites.length:0);
  const currentUser=s.auth?`${s.auth.name||s.auth.account||"-"} (${s.auth.userId||s.auth.role||"-"})`:"未登录";
  const recentSearches=(s.searches||[]).slice(0,6).map(x=>`<span class="tag tag-muted">${AppUI.escapeHtml((x.userId?x.userId+"：":"")+(x.term||x))}</span>`).join("")||'<span class="subtle-text">暂无</span>';
  const recentFavorites=(s.favorites||[]).slice(0,5).map(x=>`<div class="kv"><strong>${AppUI.escapeHtml((x.userId?x.userId+"：":"")+(x.name||x.product_id||"收藏商品"))}</strong><span>${money(x.price||0)}</span></div>`).join("")||'<div class="subtle-text">暂无收藏。</div>';
  const cartRows=s.carts.map(c=>`<div class="kv"><strong>${AppUI.escapeHtml(c.key.replace("cart_","")||"用户")}</strong><span>${Array.isArray(c.value)?c.value.length:0} 类 / ${Array.isArray(c.value)?c.value.reduce((n,p)=>n+Number(p.quantity||1),0):0} 件</span></div>`).join("")||'<div class="subtle-text">暂无购物车数据。</div>';
  els.behaviorBox.innerHTML=`<article class="info-card"><div class="info-title">当前登录用户</div><div class="kv"><strong>身份</strong><span>${AppUI.escapeHtml(currentUser)}</span></div><div class="kv"><strong>购物车件数</strong><span>${s.cartItems}</span></div><div class="kv"><strong>订单总额</strong><span>${money(s.orderAmount)}</span></div></article><article class="info-card"><div class="info-title">购物车统计</div>${cartRows}</article><article class="info-card"><div class="info-title">搜索与浏览</div><div class="kv"><strong>最近搜索</strong><span>${(s.searches||[]).length} 条</span></div><div class="kv"><strong>浏览记录</strong><span>${(s.views||[]).length} 条</span></div><div class="kv"><strong>推荐记录</strong><span>${(s.recHistory||[]).length} 条</span></div><div class="tag-row">${recentSearches}</div></article><article class="info-card"><div class="info-title">收藏商品</div>${recentFavorites}</article>`;
}

function renderCatalog(payload){
  const products=AppUI.normalizeProducts((payload&&payload.items)||[]);
  if(!products.length){els.catalogBox.innerHTML='<div class="empty-state">暂无商品数据。</div>';return;}
  els.statCatalogProducts.textContent=String((payload&&payload.total)||products.length);
  els.catalogBox.innerHTML=products.map(p=>`<article class="admin-product-row"><div><strong>${AppUI.escapeHtml(p.name)}</strong><span>${AppUI.escapeHtml(p.category||"未分类")} · ${AppUI.escapeHtml(p.brand||"未知品牌")}</span></div><div class="admin-product-meta"><b>${money(p.price)}</b><small>库存 ${AppUI.escapeHtml(String(p.stock||0))}</small></div></article>`).join("");
}

async function loadExperiments(){
  if(loading.exp)return;loading.exp=true;AppUI.setButtonBusy(els.reloadExp,true,"刷新中...","刷新实验");AppUI.setStatus(els.expState,"正在加载实验数据...","loading");
  try{const data=await AppUI.fetchJson("/api/v1/experiments",{headers:headers()});renderExperiments(data);AppUI.setStatus(els.expState,"实验数据加载完成。","ok");return data;}
  catch(e){els.expBox.innerHTML=`<div class="empty-state">加载实验失败：${AppUI.escapeHtml(e.message||"未知错误")}</div>`;AppUI.setStatus(els.expState,"实验数据刷新失败。","error");throw e;}
  finally{loading.exp=false;AppUI.setButtonBusy(els.reloadExp,false,"刷新中...","刷新实验");}
}
async function loadMetrics(){
  if(loading.metric)return;loading.metric=true;AppUI.setButtonBusy(els.reloadMetric,true,"刷新中...","刷新指标");AppUI.setStatus(els.metricState,"正在加载指标数据...","loading");
  try{const data=await AppUI.fetchJson("/api/v1/metrics",{headers:headers()});renderMetrics(data);AppUI.setStatus(els.metricState,"指标数据加载完成。","ok");return data;}
  catch(e){els.metricBox.innerHTML=`<div class="empty-state">加载指标失败：${AppUI.escapeHtml(e.message||"未知错误")}</div>`;AppUI.setStatus(els.metricState,"指标数据刷新失败。","error");throw e;}
  finally{loading.metric=false;AppUI.setButtonBusy(els.reloadMetric,false,"刷新中...","刷新指标");}
}
function loadBehavior(){
  if(loading.behavior)return;loading.behavior=true;AppUI.setButtonBusy(els.reloadBehavior,true,"刷新中...","刷新行为");AppUI.setStatus(els.behaviorState,"正在读取前台本地行为数据...","loading");
  try{renderBehavior();AppUI.setStatus(els.behaviorState,"行为统计已刷新。","ok");}
  catch(e){els.behaviorBox.innerHTML=`<div class="empty-state">加载行为统计失败：${AppUI.escapeHtml(e.message||"未知错误")}</div>`;AppUI.setStatus(els.behaviorState,"行为统计刷新失败。","error");}
  finally{loading.behavior=false;AppUI.setButtonBusy(els.reloadBehavior,false,"刷新中...","刷新行为");}
}
async function loadCatalog(){
  if(loading.catalog)return;loading.catalog=true;AppUI.setButtonBusy(els.reloadCatalog,true,"刷新中...","刷新商品");AppUI.setStatus(els.catalogState,"正在加载商品与类目...","loading");
  try{const [cats,products]=await Promise.all([AppUI.fetchApiJson("/api/v1/categories"),AppUI.fetchApiJson("/api/v1/search?page=1&page_size=200")]);renderCatalog(products);AppUI.setStatus(els.catalogState,`商品数据加载完成，类目 ${((cats&&cats.items)||[]).length} 个。`,"ok");}
  catch(e){els.catalogBox.innerHTML=`<div class="empty-state">加载商品失败：${AppUI.escapeHtml(e.message||"未知错误")}</div>`;AppUI.setStatus(els.catalogState,"商品数据刷新失败。","error");}
  finally{loading.catalog=false;AppUI.setButtonBusy(els.reloadCatalog,false,"刷新中...","刷新商品");}
}
async function refreshDashboard(){
  loadBehavior();
  const rs=await Promise.allSettled([loadMetrics(),loadCatalog()]);
  AppUI.setStatus(els.outcomeState,rs.some(r=>r.status==="rejected")?"后台已刷新，但部分面板加载失败。":"后台数据已刷新。",rs.some(r=>r.status==="rejected")?"error":"ok");
}
async function submitOutcome(e){
  e.preventDefault();const exp=els.experimentId.value.trim(),group=els.groupName.value.trim(),success=els.isSuccess.value==="true";
  if(!exp||!group){AppUI.setStatus(els.outcomeState,"实验 ID 和分组名称不能为空。","error");return;}
  AppUI.setButtonBusy(els.outcomeBtn,true,"提交中...","提交实验结果");AppUI.setStatus(els.outcomeState,"正在提交实验结果...","loading");
  try{const url=`/api/v1/experiments/${encodeURIComponent(exp)}/outcome?group=${encodeURIComponent(group)}&success=${success}`;await AppUI.fetchJson(url,{method:"POST",headers:headers()});await Promise.allSettled([loadExperiments(),loadMetrics()]);AppUI.setStatus(els.outcomeState,"实验结果已记录并刷新完成。","ok");}
  catch(err){AppUI.setStatus(els.outcomeState,"提交失败："+(err.message||"未知错误"),"error");}
  finally{AppUI.setButtonBusy(els.outcomeBtn,false,"提交中...","提交实验结果");}
}
async function login(e){
  e.preventDefault();const account=els.account.value.trim()||"admin",key=els.apiKey.value.trim();
  if(!key){AppUI.setStatus(els.loginState,"请输入管理员 API Key。","error");return;}
  adminKey=key;AppUI.setButtonBusy(els.loginBtn,true,"校验中...","登录管理员后台");AppUI.setStatus(els.loginState,"正在校验管理员身份...","loading");
  try{await AppUI.fetchJson("/api/v1/experiments",{headers:headers()});localStorage.setItem(ADMIN_KEY_STORAGE,key);localStorage.setItem(ADMIN_NAME_STORAGE,account);localStorage.setItem("novacartAuth",JSON.stringify({role:"admin",account:account,name:account,loginAt:new Date().toISOString()}));showDashboard(true);refreshDashboard();}
  catch(err){adminKey="";localStorage.removeItem(ADMIN_KEY_STORAGE);AppUI.setStatus(els.loginState,"登录失败："+(err.message||"管理员密钥不正确"),"error");}
  finally{AppUI.setButtonBusy(els.loginBtn,false,"校验中...","登录管理员后台");}
}
function logout(){
  adminKey="";if(window.AppUI&&AppUI.logoutAuth){AppUI.logoutAuth();}else{localStorage.removeItem(ADMIN_KEY_STORAGE);localStorage.removeItem(ADMIN_NAME_STORAGE);localStorage.removeItem("novacartAuth");}els.apiKey.value="";[els.statExp,els.statAgents,els.statOrders,els.statFavorites,els.statCatalogProducts].filter(Boolean).forEach(el=>el.textContent="-");window.location.href="/login?role=admin";
}
els.loginForm.addEventListener("submit",login);els.logout.addEventListener("click",logout);els.refreshAll.addEventListener("click",refreshDashboard);els.reloadExp.addEventListener("click",loadExperiments);els.reloadMetric.addEventListener("click",loadMetrics);els.reloadBehavior.addEventListener("click",loadBehavior);els.reloadCatalog.addEventListener("click",loadCatalog);els.outcomeForm.addEventListener("submit",submitOutcome);
if(hasUnifiedAdminLogin()){els.apiKey.value=adminKey;showDashboard(true);refreshDashboard();}else{window.location.href="/login?role=admin";}

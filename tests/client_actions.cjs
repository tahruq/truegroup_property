const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.join(__dirname, "..");
let checks = 0;
async function desk(file, type, doc, dirty, answer) {
  const handlers = [], buttons = [], calls = [], routes = [], drafts = [];
  const context = {__: x=>x, window: {location:{search:""}}, URLSearchParams,
    frappe: {ui:{form:{on:(dt,h)=>{if(dt===type)handlers.push(h)}}},
      msgprint:()=>{}, call:async x=>{calls.push(x);return {message:answer}},
      set_route:(...x)=>routes.push(x), new_doc:(...x)=>drafts.push(x)}};
  vm.runInNewContext(fs.readFileSync(path.join(root,"truegroup_property/public/js",file),"utf8"),context);
  const frm = {doc,is_new:()=>false,is_dirty:()=>dirty,
    add_custom_button:(label,action)=>buttons.push({label,action}),reload_doc:async()=>{}};
  for(const h of handlers) if(h.refresh) await h.refresh(frm);
  return {buttons,calls,routes,drafts};
}
(async()=>{
  let x = await desk("lead.js","CRM Lead",{name:"L1",status:"Qualified"},true,{deal:"D1"});
  await x.buttons[0].action(); assert.equal(x.calls.length,0); checks++;
  x = await desk("lead.js","CRM Lead",{name:"L1",status:"Qualified"},false,{deal:"D1"});
  await x.buttons[0].action(); assert.equal(x.calls[0].type,"POST"); assert.equal(x.routes[0][2],"D1"); checks++;
  x = await desk("deal.js","CRM Deal",{name:"D1",status:"Won"},false,{values:{crm_deal:"D1"}});
  await x.buttons.find(b=>b.label==="Review / Open Customer").action();
  assert.equal(x.drafts[0][0],"Customer"); assert.equal(x.drafts[0][1].crm_deal,"D1"); checks++;
  x = await desk("deal.js","CRM Deal",{name:"D1",status:"Qualification"},false,{});
  assert.equal(x.buttons.length,1); checks++;
  const scripts = JSON.parse(fs.readFileSync(path.join(root,"truegroup_property/configuration/crm_form_scripts.json"),"utf8"));
  for(const script of scripts) {
    const calls=[], location={href:""};
    const ctx={window:{location},encodeURIComponent,call:async(method,args)=>{
      calls.push({method,args});return {deal:"D1",customer:"C1",service_request:"R1"};
    }};
    vm.runInNewContext(script.script,ctx);
    assert.equal(ctx.setupForm({doc:{name:"X",status:"New"}}).actions.length,0); checks++;
    const actions=ctx.setupForm({doc:{name:"X",status:script.dt==="CRM Lead"?"Qualified":"Won"}}).actions;
    for(const action of actions) {await action.onClick();assert.ok(location.href.startsWith("/desk/"));checks++;}
  }
  console.log(checks+" JavaScript action checks passed");
})().catch(e=>{console.error(e);process.exitCode=1});

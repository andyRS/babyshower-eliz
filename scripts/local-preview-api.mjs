// Local preview only. Production requests are served by FastAPI and MongoDB Atlas.
import {createServer} from 'node:http';
import {randomUUID} from 'node:crypto';

const rows = [
  ['Pampers #2','Pañales y cuidado','Pañales talla 2.','baby'],['Pampers #3','Pañales y cuidado','Pañales talla 3.','baby'],['Pampers #4','Pañales y cuidado','Pañales talla 4.','baby'],['Pampers #5','Pañales y cuidado','Pañales talla 5.','baby'],['Wipes','Pañales y cuidado','Toallitas húmedas para bebé.','sparkles'],['Baberos de hombro','Ropita y textiles','Para acompañar sus comidas.','shirt'],['Mantas','Ropita y textiles','Para arropar a Eliz.','heart'],['Juego de gimnasio','Juegos y descanso','Para sus primeros juegos.','sparkles'],['Corral','Juegos y descanso','Un espacio cómodo y seguro.','baby'],['Gavetero de bebé','Habitación','Para organizar sus cositas.','gift'],['Bañito','Baño y cuidado','Bañera para bebé.','bath'],['Biberones pequeños','Alimentación','Biberones de tamaño pequeño.','milk'],['Biberones grandes','Alimentación','Biberones de tamaño grande.','milk'],['Gel de baño de bebé','Baño y cuidado','Gel suave para sus baños.','bath'],['Crema de bebé','Baño y cuidado','Crema para cuidar su piel.','heart'],['Toalla para bebé','Baño y cuidado','Una toalla suave para Eliz.','bath']
];
const gifts=rows.map(([title,category,description,icon])=>({id:randomUUID(),title,category,description,icon,quantity:1,reservations:[]}));
const publicGift=g=>({id:g.id,title:g.title,available:g.reservations.length<g.quantity});
const adminGift=g=>({...g,reserved:g.reservations.length,available:Math.max(0,g.quantity-g.reservations.length)});
const send=(res,status,body)=>{res.writeHead(status,{'Content-Type':'application/json','Access-Control-Allow-Origin':'http://127.0.0.1:5173','Access-Control-Allow-Headers':'Content-Type, Authorization','Access-Control-Allow-Methods':'GET, POST, PATCH, DELETE, OPTIONS'});res.end(JSON.stringify(body))};
createServer(async(req,res)=>{
  if(req.method==='OPTIONS')return send(res,204,{});
  let body={};try{for await(const chunk of req)body=JSON.parse(chunk.toString())}catch{}
  const path=new URL(req.url,'http://localhost').pathname;
  if(path==='/api/gifts'&&req.method==='GET')return send(res,200,gifts.map(publicGift));
  if(path==='/api/gifts/find'&&req.method==='POST'){const name=String(body.name||'').trim().replace(/\s+/g,' ');if(!/^\p{L}+(?:[-']\p{L}+)? \p{L}+(?:[-']\p{L}+)?$/u.test(name))return send(res,422,{detail:'Escribe tu primer nombre y primer apellido'});const key=s=>s.normalize('NFD').replace(/\p{M}/gu,'').toLocaleLowerCase();return send(res,200,{gifts:gifts.filter(g=>g.reservations.some(r=>key(r.name)===key(name))).map(g=>({title:g.title,category:g.category}))})}
  if(path==='/api/admin/login'&&req.method==='POST')return send(res,200,{token:'local-preview'});
  if(path.startsWith('/api/admin/')&&req.headers.authorization!=='Bearer local-preview')return send(res,401,{detail:'Acceso de administrador requerido'});
  if(path==='/api/admin/gifts'&&req.method==='GET')return send(res,200,gifts.map(adminGift));
  if(path==='/api/admin/gifts'&&req.method==='POST'){const g={...body,id:randomUUID(),reservations:[]};gifts.push(g);return send(res,200,adminGift(g))}
  const match=path.match(/^\/api\/(?:admin\/)?gifts\/([^/]+)(?:\/(reserve|reservations)(?:\/([^/]+))?)?$/);
  if(!match)return send(res,404,{detail:'No encontrado'});
  const gift=gifts.find(g=>g.id===match[1]);if(!gift)return send(res,404,{detail:'Regalo no encontrado'});
  if(match[2]==='reserve'&&req.method==='POST'){if(gift.reservations.length>=gift.quantity)return send(res,409,{detail:'Este regalo ya está completo'});const name=String(body.name||'').trim().replace(/\s+/g,' ');if(!/^\p{L}+(?:[-']\p{L}+)? \p{L}+(?:[-']\p{L}+)?$/u.test(name))return send(res,422,{detail:'Escribe tu primer nombre y primer apellido'});gift.reservations.push({id:randomUUID(),name,created_at:new Date().toISOString()});return send(res,200,{gift:publicGift(gift)})}
  if(match[2]==='reservations'&&req.method==='DELETE'){gift.reservations=gift.reservations.filter(r=>r.id!==match[3]);return send(res,200,{ok:true})}
  if(req.method==='PATCH'){if(body.quantity<gift.reservations.length)return send(res,409,{detail:'La cantidad no puede ser menor que las reservas actuales'});Object.assign(gift,body);return send(res,200,adminGift(gift))}
  if(req.method==='DELETE'){if(gift.reservations.length)return send(res,409,{detail:'Quita las reservas antes de eliminar el regalo'});gifts.splice(gifts.indexOf(gift),1);return send(res,200,{ok:true})}
  send(res,404,{detail:'No encontrado'});
}).listen(8000,'127.0.0.1',()=>console.log('Local preview API: http://localhost:8000'));

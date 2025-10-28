import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import LoginView from '../views/LoginView.vue'
import HomeView from '../views/HomeView.vue'
import InsertView from '../views/InsertView.vue'
import InspectLogsView from '../views/InspectLogsView.vue'
import ModsView from '../views/ModsView.vue'
import ModsByDateView from '../views/ModsByDateView.vue'
import QueryView from '../views/QueryView.vue'
import RagView from '../views/RagView.vue'


const routes = [
{ path:'/login', name:'login', component:LoginView, meta:{ public:true } },
{ path:'/', name:'home', component:HomeView },
{ path:'/insert', name:'insert', component:InsertView },
{ path:'/view', name:'view', component:InspectLogsView },
{ path:'/mods', name:'mods', component:ModsView },
{ path:'/mods-by-date', name:'modsByDate', component:ModsByDateView },
{ path:'/query', name:'query', component:QueryView },
{ path:'/rag', name:'rag', component:RagView }
]


const router = createRouter({ history:createWebHistory(), routes })


router.beforeEach((to) => {
const auth = useAuthStore()
if (!to.meta.public && !auth.token) return { name:'login' }
})


export default router
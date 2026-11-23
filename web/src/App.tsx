import { useEffect, useState } from 'react'
import { ArrowRight, Disc3, FileMusic, FolderHeart, Heart, Headphones, Menu, Music2, Sparkles, WandSparkles, X } from 'lucide-react'
import FullSongPage from './pages/FullSongPage'
import LyricsGeneratorPage from './pages/LyricsGeneratorPage'
import TextToSongPage from './pages/TextToSongPage'
import GeneratedFilesPage from './pages/GeneratedFilesPage'
import PricingPage from './pages/PricingPage'

type Route = 'home' | 'full-song' | 'lyrics-generator' | 'text-to-song' | 'generated-files' | 'pricing'
const routes: { id: Route; name: string; description: string; icon: typeof Music2 }[] = [
  { id: 'full-song', name: 'Music Generator', description: 'Create complete songs', icon: Music2 },
  { id: 'lyrics-generator', name: 'AI Lyrics', description: 'Write your next story', icon: WandSparkles },
  { id: 'text-to-song', name: 'Text to Song', description: 'Create instrumentals', icon: Disc3 },
  { id: 'generated-files', name: 'My Music', description: 'Your saved creations', icon: FolderHeart },
  { id: 'pricing', name: 'Plans & Licensing', description: 'Explore creator options', icon: Heart },
]
function readRoute(): Route {
  const hash = window.location.hash.replace(/^#\/?/, '')
  return (['full-song','lyrics-generator','text-to-song','generated-files','pricing'] as const).find(p => p===hash) || 'home'
}
export default function App() {
  const [route, setRoute] = useState<Route>(readRoute)
  const [menuOpen, setMenuOpen] = useState(false)
  useEffect(() => {
    const update=()=>{setRoute(readRoute());setMenuOpen(false)}
    window.addEventListener('hashchange',update)
    return ()=>window.removeEventListener('hashchange',update)
  },[])
  const go=(next:Route)=>{window.location.hash='/'+(next==='home'?'':next);setRoute(next);setMenuOpen(false);window.scrollTo(0,0)}
  return <div className="melodiva-shell">
    <aside className={'melodiva-sidebar'+(menuOpen?' is-open':'')}>
      <a className="melodiva-brand" href="#/" onClick={()=>setRoute('home')} aria-label="Melodiva AI home">
        <span className="melodiva-brand-icon"><img src="/melodiva-mark.svg" alt="" width={35} height={35}/></span>
        <span><strong>MELODIVA <em>AI</em></strong><small>CREATE THE SOUND OF YOU</small></span>
      </a>
      <div className="melodiva-nav-caption">YOUR CREATIVE STUDIO</div>
      <nav aria-label="Music creation tools">
        <a href="#/" className={'melodiva-nav-link'+(route==='home'?' is-active':'')} onClick={()=>setMenuOpen(false)}><Sparkles size={19}/> Studio Home</a>
        {routes.map(item => {const Icon=item.icon;return <a key={item.id} href={'#/'+item.id} className={'melodiva-nav-link'+(route===item.id?' is-active':'')} aria-current={route===item.id?'page':undefined} onClick={()=>setMenuOpen(false)}><Icon size={19}/>{item.name}</a>})}
      </nav>
      <div className="melodiva-sidebar-footer"><span className="melodiva-online-dot"/> Independent music generation workspace <small>Configured local AI engines required for model-backed generation.</small></div>
    </aside>
    <div className="melodiva-main">
      <header className="melodiva-topbar">
        <button type="button" className="melodiva-mobile-menu" onClick={()=>setMenuOpen(v=>!v)} aria-label={menuOpen?'Close navigation':'Open navigation'} aria-expanded={menuOpen}>{menuOpen?<X size={21}/>:<Menu size={21}/>}</button>
        <div className="melodiva-breadcrumb"><span>MELODIVA / STUDIO</span><strong>{route==='home'?'Overview':routes.find(x=>x.id===route)?.name}</strong></div>
        <a href="#/generated-files" className="melodiva-library-link"><Headphones size={17}/> My Library <ArrowRight size={14}/></a>
      </header>
      <main className="melodiva-content">
        {route==='home'&&<div className="melodiva-home">
          <section className="melodiva-hero">
            <div className="melodiva-hero-copy"><div className="melodiva-kicker"><Sparkles size={15}/> THE SOUND STARTS HERE</div><h1>Imagine it.<br/><em>Make it music.</em></h1><p>From the first lyric to the final song. Give your ideas a voice in your own creative universe.</p><button type="button" onClick={()=>go('full-song')} className="melodiva-cta">Create Your Song <ArrowRight size={18}/></button></div>
            <div className="melodiva-hero-art" aria-hidden="true"><div className="melodiva-orbit"/><div className="melodiva-disc"><Music2 size={64}/></div><div className="melodiva-wave">{Array.from({length:35},(_,i)=><i key={i} style={{height:(18+Math.abs(Math.sin(i*.32)*Math.cos(i*.17))*75)+'%' }}/>)}</div></div>
          </section>
          <div className="melodiva-section-heading"><div><div className="melodiva-kicker">YOUR POSSIBILITIES</div><h2>Everything begins with an idea.</h2></div></div>
          <div className="melodiva-tool-grid">{routes.filter(p=>p.id!=='pricing').map(item=>{const Icon=item.icon;return <button type="button" key={item.id} className="melodiva-tool-card" onClick={()=>go(item.id)}><span className="melodiva-tool-icon"><Icon size={25}/></span><strong>{item.name}</strong><small>{item.description}</small><ArrowRight size={18}/></button>})}</div>
          <div className="melodiva-message"><FileMusic size={19}/> Instrumental composition works offline; model-backed full songs and lyrics require configured engines. No fake audio generation or pre-recorded outputs.</div>
        </div>}
        {route==='full-song'&&<FullSongPage/>}
        {route==='lyrics-generator'&&<LyricsGeneratorPage/>}
        {route==='text-to-song'&&<TextToSongPage/>}
        {route==='generated-files'&&<GeneratedFilesPage/>}
        {route==='pricing'&&<PricingPage/>}
      </main>
      <footer className="melodiva-footer"><span>MELODIVA AI © {new Date().getFullYear()}</span><span>Create with intention. Only use music you have rights to.</span></footer>
    </div>
  </div>
}

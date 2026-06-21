"""Inline-JS des Reports: TOC-Scrollspy, Export (PDF/HTML), ESC schließt."""
from __future__ import annotations

JS = """
(function(){
  var menu=document.getElementById('export-menu');
  var btn=document.getElementById('btn-export');
  if(btn){btn.addEventListener('click',function(e){e.stopPropagation();menu.classList.toggle('open');});
    document.addEventListener('click',function(){menu.classList.remove('open');});}
  var pdf=document.getElementById('btn-pdf');
  if(pdf)pdf.addEventListener('click',function(){window.print();});
  var dl=document.getElementById('btn-html');
  if(dl)dl.addEventListener('click',function(){
    var blob=new Blob(['<!doctype html>'+document.documentElement.outerHTML],{type:'text/html'});
    var a=document.createElement('a');a.href=URL.createObjectURL(blob);
    a.download=(document.title||'report').replace(/[^a-z0-9]+/gi,'-')+'.html';
    a.click();URL.revokeObjectURL(a.href);
  });
  // Scrollspy: aktiven TOC-Eintrag markieren
  var links=[].slice.call(document.querySelectorAll('.toc a'));
  var heads=links.map(function(l){return document.getElementById(l.getAttribute('href').slice(1));}).filter(Boolean);
  if('IntersectionObserver' in window && heads.length){
    var spy=new IntersectionObserver(function(ents){
      ents.forEach(function(en){
        if(en.isIntersecting){
          links.forEach(function(l){l.classList.remove('active');});
          var a=document.querySelector('.toc a[href="#'+en.target.id+'"]');
          if(a)a.classList.add('active');
        }
      });
    },{rootMargin:'-10% 0px -75% 0px'});
    heads.forEach(function(h){spy.observe(h);});
  }
  document.addEventListener('keydown',function(e){if(e.key==='Escape'){try{window.close();}catch(_){}}});
})();
"""

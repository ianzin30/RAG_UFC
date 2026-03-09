*   [Skip to main content](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript#content)
    
*   [Skip to search](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript#search)
    

Esta página foi traduzida do inglês pela comunidade. [Saiba mais e junte-se à comunidade MDN Web Docs.](https://developer.mozilla.org/pt-BR/docs/MDN/Community/Contributing/Translated_content#locais_ativos)

View in English Always switch to English

JavaScript
==========

**JavaScript®** (às vezes abreviado para **JS**) é uma linguagem leve, interpretada e baseada em objetos com _[funções de primeira classe](http://en.wikipedia.org/wiki/First-class_function)
,_ mais conhecida como a linguagem de script para páginas Web, mas usada também em [vários outros ambientes sem browser](http://en.wikipedia.org/wiki/JavaScript#Uses_outside_web_pages)
, tais como [node.js](https://nodejs.org/)
, [Apache CouchDB](https://couchdb.apache.org/)
 e Adobe Acrobat. O JavaScript é uma linguagem [baseada em protótipos](https://en.wikipedia.org/wiki/Prototype-based)
, [multi-paradigma](https://en.wikipedia.org/wiki/Programming_paradigm)
 e dinâmica, suportando estilos de orientação a objetos, imperativos e declarativos (como por exemplo a programação funcional). Saiba mais [sobre o JavaScript](https://developer.mozilla.org/pt-BR/docs/conflicting/Web/JavaScript)
.

Essa seção do site é dedicada à linguagem JavaScript e não às partes que são específicas para páginas Web e outros ambientes. Para mais informações sobre as [APIs](https://developer.mozilla.org/pt-BR/docs/Glossary/API)
 específicas para páginas Web, por favor consulte as seções [Web APIs](https://developer.mozilla.org/pt-BR/docs/Web/API)
 e [DOM](https://developer.mozilla.org/pt-BR/docs/Glossary/DOM)
.

O padrão JavaScript é [ECMAScript](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/JavaScript_technologies_overview)
. Desde 2012, todos os [navegadores modernos](http://kangax.github.io/compat-table/es5/)
 possuem suporte total ao ECMAScript 5.1. Navegadores mais antigos suportam pelo menos ECMAScript 3. Em 17 de Junho de 2015, a [ECMA International](https://www.ecma-international.org/)
 publicou a sexta versão do ECMAScript, que é oficialmente chamado de ECMAScript 2015, e foi inicialmente conhecido como ECMAScript 6 ou ES6. Desde então, as especificações do ECMAScript são lançadas anualmente. Essa documentação faz referência à última versão de referência, que atualmente é a [ECMAScript 2018](https://tc39.github.io/ecma262/)
.

Não se deve confundir o JavaScript com a [linguagem de programação Java](https://en.wikipedia.org/wiki/Java_(programming_language))
. Tanto _Java_ quanto _JavaScript_ são marcas registradas da Oracle nos Estados Unidos da América e em outros países. No entanto, as duas linguagens de programação possuem sintaxe, semânticas e usos muito diferentes.

[Tutoriais](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript#tutoriais)

-------------------------------------------------------------------------------

Aprenda a programar em JavaScript com guias e tutoriais.

### [Para iniciantes](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript#para_iniciantes)

Vá para a [Área de aprendizado de JavaScript](https://developer.mozilla.org/pt-BR/docs/conflicting/Learn_web_development/Core/Scripting_785964b4c0711553d2bf3130baef052c6d78a03b4ce249eeb9d1ce2be1e3c308)
 se você quer aprender JavaScript mas não tem experiência prévia com JavaScript ou programação. Os módulos completos que estão disponíveis lá são os seguintes:

[Primeiros passos em JavaScript](https://developer.mozilla.org/pt-BR/docs/Learn_web_development/Core/Scripting)

Respostas para algumas perguntas básicas como _O que é JavaScript?_, _Com o que se parece?_ e _O que se pode fazer?_, bem como funcionalidades importantes do JavaScript, tais como variáveis, strings, números e vetores.

[Elementos básicos do JavaScript](https://developer.mozilla.org/pt-BR/docs/conflicting/Learn_web_development/Core/Scripting)

Continuamos nossa cobertura das funcionalidades fundamentais do JavaScript, direcionando nossa atenção para tipos de blocos de código encontrados comumente, como expressões condicionais, laços, funções e eventos.

[Introduzindo objetos em JavaScript](https://developer.mozilla.org/pt-BR/docs/Learn_web_development/Extensions/Advanced_JavaScript_objects)

O entendimento da natureza da orientação à objetos do JavaScript é importante se você quiser levar o seu conhecimento da linguagem para o próximo nível e escrever códigos mais eficientes, por isso oferecemos esse módulo para te ajudar.

### [Guia do JavaScript](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript#guia_do_javascript)

[Guia do JavaScript](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Guide)

Um guia muito mais detalhado sobre a linguagem JavaScript, para pessoas que possuem experiência prévia com JavaScript ou outra linguagem de programação.

### [Intermediário](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript#intermedi%C3%A1rio)

[Uma re-introdução ao JavaScript](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Guide/Language_overview)

Uma visão geral para aqueles que _pensam_ que conhecem JavaScript.

[Estruturas de dados do JavaScript](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Guide/Data_structures)

Um resumo das estruturas de dados disponíveis em JavaScript.

[Comparações de igualdade e uniformidade](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Guide/Equality_comparisons_and_sameness)

O JavaScript fornece três operações diferentes para comparar valores: igualdade estrita utilizando `===`, igualdade ampla usando `==` e o método [`Object.is()`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Global_Objects/Object/is)
.

### [Avançado](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript#avan%C3%A7ado)

[Herança e a cadeia de protótipos](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Guide/Inheritance_and_the_prototype_chain)

Explicação da herança baseada em protótipos, que costuma ser amplamente mal entendida e subestimada.

[Modo estrito](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Strict_mode)

O modo estrito define que você não pode usar nenhuma variável antes de inicializá-la. É uma variante restrita do ECMAScript 5, para um desempenho mais performático e uma depuração mais fácil.

[Vetores JavaScript tipados](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Guide/Typed_arrays)

Vetores JavaScript tipados oferecem um mecanismo para acesso a dados binários brutos.

[Gerenciamento de memória](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Guide/Memory_management)

Ciclo de vida da memória e coleta de lixo em JavaScript.

[Modelo de concorrência e o loop de eventos](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Execution_model)

JavaScript tem um modelo de concorrência baseado em _loop de eventos_.

[Referência](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript#refer%C3%AAncia)

--------------------------------------------------------------------------------------

Navegue pela documentação completa da [Referência de JavaScript](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference)
.

[Objetos globais](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Global_Objects)

Conheça os objetos padrão nativos [`Array`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Global_Objects/Array)
, [`Boolean`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Global_Objects/Boolean)
, [`Date`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Global_Objects/Date)
, [`Error`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Global_Objects/Error)
, [`Function`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Global_Objects/Function)
, [`JSON`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Global_Objects/JSON)
, [`Math`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Global_Objects/Math)
, [`Number`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Global_Objects/Number)
, [`Object`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Global_Objects/Object)
, [`RegExp`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Global_Objects/RegExp)
, [`String`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Global_Objects/String)
, [`Map`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Global_Objects/Map)
, [`Set`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Global_Objects/Set)
, [`WeakMap`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Global_Objects/WeakMap)
 e [`WeakSet`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Global_Objects/WeakSet)
, entre outros.

[Expressões e operadores](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Operators)

Saiba mais sobre o comportamento dos operadores de JavaScript [`instanceof`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Operators/instanceof)
, [`typeof`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Operators/typeof)
, [`new`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Operators/new)
, [`this`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Operators/this)
, a [precedência dos operadores](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Operators/Operator_precedence)
 e muito mais.

[Instruções e declarações](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Statements)

Saiba como [`do-while`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Statements/do...while)
, [`for-in`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Statements/for...in)
, [`for-of`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Statements/for...of)
, [`try-catch`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Statements/try...catch)
, [`let`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Statements/let)
, [`var`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Statements/var)
, [`const`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Statements/const)
, [`if-else`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Statements/if...else)
, [`switch`](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Statements/switch)
 e outras instruções e palavras-chave do JavaScript funcionam.

[Funções](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/Functions)

Aprenda como trabalhar com funções em JavaScript para desenvolver suas aplicações.

[Ferramentas & recursos](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript#ferramentas_recursos)

-------------------------------------------------------------------------------------------------------

Ferramentas úteis para escrever e depurar seu código **JavaScript**.

[Ferramentas do Firefox para desenvolvedores](https://firefox-source-docs.mozilla.org/devtools-user/index.html)

Scratchpad, [Web Console](https://firefox-source-docs.mozilla.org/devtools-user/web_console/index.html)
, [JavaScript Profiler](https://firefox-source-docs.mozilla.org/devtools-user/performance/index.html)
, [Debugger](https://firefox-source-docs.mozilla.org/devtools-user/debugger/index.html)
 e muito mais.

[JavaScript Shells](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Reference/JavaScript_technologies_overview)

Um shell JavaScript permite que você teste rapidamente fragmentos de código JavaScript.

[TogetherJS](https://togetherjs.com/)

Colaboração fácil. Ao adicionar o TogetherJS ao seu site, seus usuários podem ajudar uns aos outros em tempo real!

[Stack Overflow](https://stackoverflow.com/questions/tagged/javascript)

Perguntas do Stack Overflow com a tag _JavaScript_.

Versões do JavaScript e notas de lançamento

Navegue no histórico de funcionalidades do JavaScript e no status das implementações.

[JSFiddle](https://jsfiddle.net/)

Edite JavaScript, CSS e HTML e obtenha resultados em tempo real. Utilize recursos externos e colabore com sua equipe online.

Help improve MDN
----------------

[Learn how to contribute](https://developer.mozilla.org/pt-BR/docs/MDN/Community/Getting_started)

This page was last modified on 27 de abr. de 2025 by [MDN contributors](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/contributors.txt)
.

[View this page on GitHub](https://github.com/mdn/translated-content/blob/main/files/pt-br/web/javascript/index.md?plain=1 "Folder: pt-br/web/javascript (Opens in a new tab)")
 • [Report a problem with this content](https://github.com/mdn/translated-content/issues/new?template=page-report-pt-br.yml&mdn-url=https%3A%2F%2Fdeveloper.mozilla.org%2Fpt-BR%2Fdocs%2FWeb%2FJavaScript&metadata=%3C%21--+Do+not+make+changes+below+this+line+--%3E%0A%3Cdetails%3E%0A%3Csummary%3EPage+report+details%3C%2Fsummary%3E%0A%0A*+Folder%3A+%60pt-br%2Fweb%2Fjavascript%60%0A*+MDN+URL%3A+https%3A%2F%2Fdeveloper.mozilla.org%2Fpt-BR%2Fdocs%2FWeb%2FJavaScript%0A*+GitHub+URL%3A+https%3A%2F%2Fgithub.com%2Fmdn%2Ftranslated-content%2Fblob%2Fmain%2Ffiles%2Fpt-br%2Fweb%2Fjavascript%2Findex.md%0A*+Last+commit%3A+https%3A%2F%2Fgithub.com%2Fmdn%2Ftranslated-content%2Fcommit%2F5a4dfb62def65e26e036d5d07ed4ba525e6d7225%0A*+Document+last+modified%3A+2025-04-27T12%3A51%3A34.000Z%0A%0A%3C%2Fdetails%3E "This will take you to GitHub to file a new issue.")
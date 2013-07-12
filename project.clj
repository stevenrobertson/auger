(defproject auger "0.1.0-SNAPSHOT"
  :description "FIXME: write description"
  :url "http://example.com/FIXME"
  :license {:name "Eclipse Public License"
            :url "http://www.eclipse.org/legal/epl-v10.html"}
  :plugins [[lein-cljsbuild "0.3.2"]]
  :dependencies [[org.clojure/clojure "1.5.1"]
                 [aleph "0.3.0-rc2"]
                 [ring/ring-core "1.2.0-RC1"]
                 [hiccup "1.0.3"]
                ]
  :cljsbuild {:builds [{:source-paths ["src-cljs"]
                        :compiler {:output-dir "static/js"
                                   :output-to "static/js/deps.js"}}]}
  :main auger.core)

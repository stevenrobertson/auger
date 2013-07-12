(ns auger.core
  [:use
   lamina.core
   aleph.http

   hiccup.core
   [ring.middleware.file :only [file-request]]
  ]
  [:require
   [hiccup.page]
  ]
  (:gen-class))

(defonce current-server (agent nil))

(defn dev-page [chan req]
  (enqueue chan
    {:status 200
     :headers {"content-type" "text/html"}
     :body
      (hiccup.page/html5
        [:head
         (hiccup.page/include-js "static/js/deps.js")]
        [:body
          [:span "wtf"]])}))

(defn missing-handler [chan req]
  (enqueue chan
    {:status 404
     :body "Not found"}))

(defn ^:dynamici handler
  "Primary handler for the app."
  [chan req]
  (let [dest-handler
          (cond
            (= (:uri req) "/") dev-page
            (.startsWith (:uri req) "/static/")
              (wrap-ring-handler #(file-request %1 "."))
            :else missing-handler)
        ]
    (if dest-handler (dest-handler chan req))))

(defn ^:dynamic trampoline-handler
  "Rebinds local namespace for REPL reloading."
  [chan req]
  (handler chan req))

(defn restart-server []
  (send current-server
    (fn [old-server] do
      (when old-server (old-server))
      (start-http-server trampoline-handler {:port 8085}))))

(defn -main
  "I don't do a whole lot ... yet."
  [& args]
  (restart-server)
)

apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: ouroboros
  labels:
    app: ouroboros
spec:
  replicas: 1
  template:
    metadata:
      labels:
        app: ouroboros
    spec:
      containers:
      - name: ouroboros-app
        # Replace this with your project ID
        image: gcr.io/GOOGLE_CLOUD_PROJECT/ouroboros:COMMIT_SHA
        imagePullPolicy: Always
        env:
          - name: DATABASE_USER
            valueFrom:
              secretKeyRef:
                name: cloudsql
                key: username
          - name: DATABASE_PASSWORD
            valueFrom:
              secretKeyRef:
                name: cloudsql
                key: password
          - name: SECRET_KEY
            valueFrom:
              secretKeyRef:
                name: django-sk
                key: secret_key
          - name: SENDGRID_API_KEY
            valueFrom:
              secretKeyRef:
                name: sendgrid
                key: apikey
          - name: GOOGLE_APPLICATION_CREDENTIALS
<<<<<<< HEAD
<<<<<<< HEAD
            value: "/etc/storage-creds/django-storages-creds.json"
=======
            value: "/etc/django-storage-creds.json"
=======
            value: "/etc/storage-creds/django-storages-creds.json"
>>>>>>> Fixed volume, I think.
        volumeMounts:
          - name: django-storage-credentials
            mountPath: /etc/storage-creds
            readOnly: true
        ports:
        - containerPort: 8080
      - image: gcr.io/cloudsql-docker/gce-proxy:1.05
        name: cloudsql-proxy
        command: ["/cloud_sql_proxy", "--dir=/cloudsql",
                  "-instances=GOOGLE_CLOUD_PROJECT:us-central1:ouroboros=tcp:5432",
                  "-credential_file=/secrets/cloudsql/credentials.json"]
>>>>>>> Changed Kubernetes template.
        volumeMounts:
          - name: django-storage-credentials
            mountPath: /etc/storage-creds
            readOnly: true
        ports:
                  "-credential_file=/secrets/cloudsql/credentials.json"]
            mountPath: /etc/ssl/certs
          - name: cloudsql
            mountPath: /cloudsql
      volumes:
        - name: cloudsql-oauth-credentials
          secret:
            secretName: cloudsql-oauth-credentials
        - name: ssl-certs
          hostPath:
            path: /etc/ssl/certs
        - name: cloudsql
          emptyDir:
        - name: django-storage-credentials
          secret:
            secretName: django-storages-creds

---

# [START service]
# The ouroboros service provides a load-balancing proxy over the ouroboros app
# pods. By specifying the type as a 'LoadBalancer', Container Engine will
# create an external HTTP load balancer.
# For more information about Services see:
#   https://cloud.google.com/container-engine/docs/services/
# For more information about external HTTP load balancing see:
#   https://cloud.google.com/container-engine/docs/load-balancer
apiVersion: v1
kind: Service
metadata:
  name: ouroboros
  labels:
    app: ouroboros
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: ouroboros
# [END service]
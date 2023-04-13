import base64
from locust import HttpUser, task, between

class MyUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        username = "user"
        password = "cordoba57"
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        self.headers = {"Authorization": f"Basic {credentials}"}

    @task
    def index_page(self):
        self.client.get("https://phys.pro", headers=self.headers)

    @task
    def var(self):
        self.client.get("https://phys.pro/variants", headers=self.headers)

    #@task
    #def var2(self):
        #self.client.get("https://phys.pro/variants/2", headers=self.headers)

    #@task
    #def var1(self):
        #self.client.get("https://phys.pro/variants/1", headers=self.headers)

    @task
    def p237(self):
        self.client.get("https://phys.pro/problems/237", headers=self.headers)

    @task
    def about(self):
        self.client.get("https://phys.pro/about", headers=self.headers)

    @task
    def some_page(self):
        self.client.get("https://phys.pro/problems", headers=self.headers)

    @task
    def page1(self):
        self.client.get("https://phys.pro/problems/?page=1", headers=self.headers)

    @task
    def page2(self):
        self.client.get("https://phys.pro/problems/?page=2", headers=self.headers)

    @task
    def page3(self):
        self.client.get("https://phys.pro/problems/?page=3", headers=self.headers)

    @task
    def page4(self):
        self.client.get("https://phys.pro/problems/?page=4", headers=self.headers)

    @task
    def page5(self):
        self.client.get("https://phys.pro/problems/?page=5", headers=self.headers)

    @task
    def page6(self):
        self.client.get("https://phys.pro/problems/?page=6", headers=self.headers)

    @task
    def page7(self):
        self.client.get("https://phys.pro/problems/?page=7", headers=self.headers)


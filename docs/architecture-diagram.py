"""Generate the cloud architecture PNG diagram.

Run from the docs/ directory:

    pip install diagrams
    python architecture-diagram.py

Requires Graphviz (the ``dot`` binary) to be available on PATH.
The output file ``architecture-diagram.png`` is committed to the repo.
"""

from __future__ import annotations

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.integration import Eventbridge
from diagrams.aws.network import APIGateway, CloudFront
from diagrams.aws.security import Cognito
from diagrams.aws.storage import S3
from diagrams.onprem.client import Users

GRAPH_ATTR = {
    "fontsize": "16",
    "labelloc": "t",
    "pad": "0.5",
    "splines": "spline",
}


def main() -> None:
    with Diagram(
        "Serverless Dashboard - AWS Architecture",
        filename="architecture-diagram",
        outformat="png",
        show=False,
        graph_attr=GRAPH_ATTR,
    ):
        users = Users("End users / external systems")

        with Cluster("Frontend (static SPA)"):
            cf = CloudFront("CloudFront")
            s3 = S3("S3 (private)")
            cf >> Edge(label="OAC") >> s3

        with Cluster("Backend (HTTP API + Lambdas)"):
            api = APIGateway("API Gateway HTTP API")

            with Cluster("Auth"):
                fn_register = Lambda("auth/register")
                fn_login = Lambda("auth/login")

            with Cluster("App"):
                fn_me = Lambda("users/me")
                fn_stats = Lambda("dashboard/stats")

            with Cluster("Integrations"):
                fn_webhook = Lambda("integrations/webhook")
                fn_dispatch = Lambda("integrations/dispatch")

            api >> [fn_register, fn_login, fn_me, fn_stats, fn_webhook, fn_dispatch]

        cognito = Cognito("Cognito User Pool")
        ddb = Dynamodb("DynamoDB (single table)")
        bus = Eventbridge("EventBridge bus")

        users >> Edge(label="HTTPS") >> cf
        users >> Edge(label="HTTPS / Bearer JWT") >> api
        users >> Edge(label="HTTPS / X-API-Key") >> fn_webhook

        api >> Edge(label="JWT authorizer") >> cognito
        fn_register >> cognito
        fn_login >> cognito

        [fn_me, fn_stats, fn_webhook, fn_dispatch] >> ddb
        fn_dispatch >> bus


if __name__ == "__main__":
    main()

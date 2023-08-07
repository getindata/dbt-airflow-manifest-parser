from os import path
from unittest.mock import MagicMock, patch

import pytest

from dbt_airflow_factory.constants import (
    IS_AIRFLOW_NEWER_THAN_2_4,
    IS_FIRST_AIRFLOW_VERSION,
)
from dbt_airflow_factory.notifications.ms_teams_webhook_operator import (
    MSTeamsWebhookOperator,
)

if IS_FIRST_AIRFLOW_VERSION:
    from airflow.contrib.operators.slack_webhook_operator import SlackWebhookOperator
else:
    from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator

from dbt_airflow_factory.airflow_dag_factory import AirflowDagFactory
from dbt_airflow_factory.notifications.handler import NotificationHandlersFactory


@pytest.mark.parametrize(
    "config_dir",
    (
        "notifications_slack",
        "notifications_teams",
    ),
)
def test_notification_callback_creation(config_dir):
    # given
    factory = AirflowDagFactory(path.dirname(path.abspath(__file__)), config_dir)

    # when
    dag = factory.create()

    # then
    assert dag.default_args["on_failure_callback"]


@patch(
    "airflow.hooks.base.BaseHook.get_connection"
    if IS_AIRFLOW_NEWER_THAN_2_4
    else "airflow.hooks.base_hook.BaseHook.get_connection"
)
@patch(
    "airflow.contrib.operators.slack_webhook_operator.SlackWebhookOperator.__new__"
    if IS_FIRST_AIRFLOW_VERSION
    else "airflow.providers.slack.operators.slack_webhook.SlackWebhookOperator.__new__"
)
def test_notification_send_for_slack(mock_operator_init, mock_get_connection):
    # given
    notifications_config = AirflowDagFactory(
        path.dirname(path.abspath(__file__)), "notifications_slack"
    ).airflow_config["failure_handlers"]
    factory = NotificationHandlersFactory()
    context = create_slack_context()
    mock_get_connection.return_value = create_connection()
    mock_operator = MagicMock()
    mock_operator_init.return_value = mock_operator

    # when
    factory.create_failure_handler(notifications_config)(context)

    # then
    mock_operator_init.assert_called_once_with(
        SlackWebhookOperator,
        task_id="slack_failure_notification",
        message=":red_circle: Task Failed.\n"
        "*Task*: task_id\n"
        "*Dag*: dag_id\n"
        "*Execution Time*: some date\n"
        "*Log Url*: log_url",
        http_conn_id="slack_failure",
        webhook_token="test_password",
        username="test_login",
    )
    mock_operator.execute.assert_called_once_with(context=context)


@patch(
    "airflow.hooks.base.BaseHook.get_connection"
    if IS_AIRFLOW_NEWER_THAN_2_4
    else "airflow.hooks.base_hook.BaseHook.get_connection"
)
@patch("dbt_airflow_factory.notifications.ms_teams_webhook_operator.MSTeamsWebhookOperator.__new__")
def test_notification_send_for_teams(mock_operator_init, mock_get_connection):
    # given
    notifications_config = AirflowDagFactory(
        path.dirname(path.abspath(__file__)), "notifications_teams"
    ).airflow_config["failure_handlers"]
    factory = NotificationHandlersFactory()
    context = create_teams_context()
    mock_get_connection.return_value = create_connection()
    mock_operator = MagicMock()
    mock_operator_init.return_value = mock_operator

    # when
    factory.create_failure_handler(notifications_config)(context)

    # then
    mock_operator_init.assert_called_once_with(
        MSTeamsWebhookOperator,
        task_id="teams_failure_notification",
        message="&#x1F534; **Task Failed** <br><br>\n"
        "**Task**: task_id <br>\n**Dag**: dag_id <br>\n"
        "**Execution Time**: some date <br>\n"
        "**Log Url**: https://your.airflow-webserver.url/log?dag_id=dag_id&task_id=task_id&execution_date=ts",
        http_conn_id="teams_failure",
        button_text="View log",
        button_url="https://your.airflow-webserver.url/log?dag_id=dag_id&task_id=task_id&execution_date=ts",
        theme_color="FF0000",
    )
    mock_operator.execute.assert_called_once_with(context)


def create_connection():
    connection = MagicMock()
    connection.configure_mock(**{"login": "test_login", "password": "test_password"})
    return connection


def create_slack_context():
    task_instance = MagicMock()
    task_instance.configure_mock(**{"task_id": "task_id", "dag_id": "dag_id", "log_url": "log_url"})
    return {"task_instance": task_instance, "execution_date": "some date"}


def create_teams_context():
    task_instance = MagicMock()
    task_instance.configure_mock(
        **{
            "task_id": "task_id",
            "dag_id": "dag_id",
            "log_url": "log_url",
        }
    )
    return {"task_instance": task_instance, "execution_date": "some date", "ts": "ts"}

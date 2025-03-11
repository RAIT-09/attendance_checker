// 下の変数はちゃんと変更する
///////////////////////////////////////////////////////////////////////////////////////
const FORM_SHEET_ID = 'xxxxxx'; // 申請フォームの回答スプレッドシートのID
const ATTENDANCE_SHEET_ID = 'xxxxxx'; // 出席管理スプレッドシートのID
const SLACK_TOKEN = 'xoxb-xxxxxx'; // Slack Botのトークン
const APPROVAL_CHANNEL_ID = 'xxxxxxx'; // グループリーダーのDMチャンネルのID
const ATTENDANCE_CHANNEL_ID = 'xxxxxxx'; // 20xxgr1_attendanceチャンネルのID
///////////////////////////////////////////////////////////////////////////////////////




const formSheet = SpreadsheetApp.openById(FORM_SHEET_ID).getSheetByName('Form Responses');
const attendanceSheet = SpreadsheetApp.openById(ATTENDANCE_SHEET_ID).getSheetByName('Sheet1');

// フォーム送信時に承認リクエストを送る
function onFormSubmit(e) {
  const responses = e.values;
  const studentId = responses[1];
  const mtgDate = responses[2];
  const status = responses[3];
  const reason = responses[4];
  const name = responses[5];

  const dataRange = attendanceSheet.getDataRange();
  const values = dataRange.getValues();
  
  // 学籍番号がシートに存在するかチェック
  let studentExists = false;
  for (let j = 1; j < values[2].length; j++) { // 3行目から学籍番号列を探す
    if (values[2][j] == studentId) { // 学籍番号が一致したら
      studentExists = true;
      break;
    }
  }

  // 学籍番号が存在しない場合、エラーメッセージを表示
  if (!studentExists) {
    sendSlackMessageToChannel(APPROVAL_CHANNEL_ID, `⚠️ ${name} さんの学籍番号 (${studentId}) が登録されていません。\n番号が正しいか確認し、再申請してください。`, null);
    return; // 処理を終了
  }

  sendApprovalRequestToSlack(studentId, mtgDate, status, reason, name);
}

// Slack に承認リクエストを送る
function sendApprovalRequestToSlack(studentId, mtgDate, status, reason, name) {
  const messageText = `${name} (${studentId}) の出席状況に関して承認をお願いします。\nMTG日時: ${mtgDate}\n状況: ${status}\n理由: ${reason}`;
  const attachments = [
    {
      text: '承認しますか？',
      fallback: '承認ボタンを押してください',
      callback_id: 'attendance_approval',
      actions: [
        { name: 'approve', text: '承認', type: 'button', value: `${name},${studentId},${mtgDate},${status},${reason}`},
        { name: 'reject', text: '拒否', type: 'button', value: `${name},${studentId},${mtgDate},${status},${reason}`}
      ]
    }
  ];

  sendSlackMessageToChannel(APPROVAL_CHANNEL_ID, messageText, attachments);
}

// Slack にメッセージを送信する汎用関数
function sendSlackMessageToChannel(channel, text, attachments) {
  const message = {
    channel: channel,
    text: text,
    attachments: attachments || []  // attachments はオプション
  };

  const options = {
    method: 'post',
    contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + SLACK_TOKEN },
    payload: JSON.stringify(message)
  };

  UrlFetchApp.fetch('https://slack.com/api/chat.postMessage', options);
}

// Slackからの承認or拒否イベントを受け取る
// doPostはGASのWebアプリでPOSTリクストを処理する際に呼ばれる関数名
function doPost(e) {
  // URLデコードしてからJSONにパース
  let decodedPayload = decodeURIComponent(e.postData.contents);
  decodedPayload = decodedPayload.replace(/^payload=/, '');
  const data = JSON.parse(decodedPayload);
  
  const actions = data.actions[0];  // actions配列の最初の要素を取得
  const value = actions.value.split(',');  // valueは「学籍番号,日付,状態」の形式なのでsplitで分割
  const name = decodeURIComponent(value[0])
  const studentId = value[1];
  const mtgDate = value[2];
  const status = decodeURIComponent(value[3]);
  const reason = decodeURIComponent(value[4])
  const buttonType = actions.name;

  const responseUrl = data.response_url; // メッセージ更新用の URL
  let newMessage;

  if (buttonType == "approve") {
    writeToAttendanceSheet(mtgDate, studentId, status, reason);

    newMessage = {
      replace_original: true,
      text: `✅ ${name} (${studentId}) の ${mtgDate} における ${status} を **承認** しました！\n(理由: ${reason})`
    };

    sendSlackMessageToChannel(ATTENDANCE_CHANNEL_ID, `✅ ${name} (${studentId}) の${mtgDate}における${status}が承認されました\n(理由：${reason})`, null);
  } else {
    newMessage = {
      replace_original: true,
      text: `❌ ${name} (${studentId}) の ${mtgDate} における ${status} を **拒否** しました！`
    };

    newMessage = {
      replace_original: true,
      text: `❌ ${name} (${studentId}) の ${mtgDate} における ${status} を **拒否** しました！`
    };

    sendSlackMessageToChannel(ATTENDANCE_CHANNEL_ID, `❌ ${name} (${studentId}) の${mtgDate}における${status}が否認されました`, null);
  }

  UrlFetchApp.fetch(responseUrl, {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(newMessage)
  });

  return ContentService.createTextOutput("").setMimeType(ContentService.MimeType.TEXT);
}

// スプレッドシートに出席を記録
function writeToAttendanceSheet(mtgDate, studentId, status, reason) {
  const sheet = attendanceSheet;
  const dataRange = sheet.getDataRange();
  const values = dataRange.getValues();

  const mtgDateObj = new Date(mtgDate);
  // A列（4行目以降）からmtgDateを探す
  let dateRow = -1;
  for (let i = 3; i < values.length; i++) {
    const sheetDateObj = new Date(values[i][0]);
    if (sheetDateObj.getMonth() === mtgDateObj.getMonth() &&
        sheetDateObj.getDate() === mtgDateObj.getDate()) {
      dateRow = i + 1; // シート上の行番号
      break;
    }
  }

  // 見つからなければ新しい行を追加
  if (dateRow === -1) {
    dateRow = values.length + 1; // 新しい行を追加
    sheet.getRange(dateRow, 1).setValue(mtgDate);
  }

  // 3行目からstudentIdを探す
  let studentCol = -1;
  for (let j = 1; j < values[2].length; j++) {
    if (values[2][j] == studentId) {
      studentCol = j + 1; // シート上の列番号
      break;
    }
  }

  // statusを書き込む
  const targetCell = sheet.getRange(dateRow, studentCol);
  targetCell.setValue(status);
  targetCell.setComment(reason);
}

// Slack に通知を送る
function sendSlackMessage(channel, message) {
  const payload = {
    channel: channel,
    text: message
  };

  const options = {
    method: 'post',
    contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + SLACK_TOKEN },
    payload: JSON.stringify(payload)
  };

  UrlFetchApp.fetch('https://slack.com/api/chat.postMessage', options);
}

// 承認・拒否のレスポンスを Slack に返す
function sendSlackResponse(responseUrl, text) {
  const payload = {
    text: text,
    replace_original: true
  };

  const options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload)
  };

  UrlFetchApp.fetch(responseUrl, options);
}
from flask import Flask, render_template, request, redirect, session, url_for, flash
from pymongo import MongoClient
from datetime import datetime, timedelta
from pytz import timezone
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = "your-super-secret-key" # 세션 쓰기위한 시크릿 키 임의로 설정함
client = MongoClient('localhost',27017)  # mongoDB는 27017 포트로 돌아갑니다.
db = client.week_study_king  # db를 만들거나 사용합니다.


#메인페이지 및 입실 퇴실 상태 관리 및 상위 랭킹 5명 관리
@app.route('/')
def home():
    userid = session.get("userid")
    if userid:
        user = db.users.find_one({"userid": userid})
    else:
        user = None
        
    now = datetime.now( )
    today = now.date()
    
    #입실시간(enter_time)의 상태를 보고 입퇴실 상태 알 수 있음
    enter_time = user.get("enter_time") if user else None
    
    can_checkin = user and enter_time is None
    can_checkout = user and enter_time and enter_time.date() == today


    # 상위 5명 표시
    # MongoDB에서 상위 5명만 가져오기
    top_users = list(db.users.find({}, {"userid": 1, "username": 1, "study_time": 1})
                     .sort("study_time", -1)  # 공부 시간 기준 내림차순 정렬
                     .limit(5))  # 상위 5명만 가져오기
    for users in top_users:
        total_seconds = users.get("study_time", 0)
        users["hours"] = int(total_seconds // 3600)
        users["minutes"] = int((total_seconds % 3600) // 60)
        users["seconds"] = int(total_seconds % 60)


    return render_template("Rank.html",
                           can_checkin = can_checkin,
                           can_checkout = can_checkout,
                           is_logged_in = bool(user),
                           rankings = top_users)

#입퇴실 관련 라우트
@app.route('/check_in_out',methods = ["POST"])
def check_in_out():
    #서버에서도 로그인 상태 검사
    userid = session.get("userid")
    if not userid:
        flash("로그인 후 이용해주세요.", "danger")
        return redirect(url_for("home"))
    
    action = request.form.get("action")
    now = datetime.now( )
    user = db.users.find_one({"userid": userid})
    
    #DB에 유저 있는지 확인
    if not user:
        flash("사용자를 찾을 수 없습니다.", "danger")
        return redirect(url_for("home"))
    
    # 입실
    if action == "checkin":
        if user.get("enter_time") is None:
            db.users.update_one(
                {"userid": userid},
                {"$set": {"enter_time": now}}
            )
            flash("입실 완료!", "success")
        else:
            flash("이미 입실 중입니다.", "warning")

    # 퇴실
    elif action == "checkout":
        enter_time = user.get("enter_time")
        if enter_time:
            #퇴실 시 입실시간부터 지금까지 시간 계산해서 출력 및 이번 주 공부 시간에 합산
            duration = (now.replace(tzinfo=None) - enter_time).total_seconds()
            db.users.update_one(
                {"userid": userid},
                {
                    "$inc": {"study_time": int(duration)},
                    "$set": {"enter_time": None}
                }
            )
            flash(f"퇴실 완료! 오늘 공부한 시간: {int(duration // 3600)}시간 {int((duration%3600) // 60)}분 {int(duration % 60)}초", "success")
        else:
            flash("입실 기록이 없습니다.", "warning")

    return redirect(url_for("home"))




#로그인 관련
@app.route('/login',methods = ["GET", "POST"])
def login():
    if request.method == "POST": #post 일때
        userid = request.form.get('userid')
        password = request.form.get('password')
        
        user = db.users.find_one({"userid" : userid})
        if user and check_password_hash(user["password"], password):
            session["userid"] = userid # 세션인 경우 여기에 로그인 상태 저장
            flash("로그인 성공!")
            return redirect('/')
        else:
            flash("로그인 실패")
            
    # 로그인 페이지로 이동 GET일때
    return render_template("Login.html")
 
 
        
#회원가입 관련
@app.route('/register',methods = ["GET", "POST"])
def register():
    # 이름 아이디 비번 입력 후 회원가입요청 POST
    if request.method == "POST":
        username = request.form.get('username')
        userid = request.form.get('userid')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        db_id = db.users.find_one({"userid": userid})
        if db_id:
            flash("중복된 아이디가 존재합니다. 다른 아이디를 입력해주세요.")
            return redirect(url_for("register"))
        if password != confirm_password:
            flash("비밀번호가 일치하지 않습니다.")
            return redirect(url_for("register"))
        
        hashed_pw = generate_password_hash(password)
        #DB에 입력
        user = {'username': username, "userid":userid, 'password': hashed_pw,
                'enter_time': None , 'goal_time': 0, 'study_time': 0}
            
        db.users.insert_one(user)
        flash("회원가입이 완료되었습니다.")
        return redirect(url_for("login"))
    
    # 회원가입 페이지로 이동 GET
    return render_template("Register.html")

@app.route("/logout")
def logout():
    session.clear()  # 세션 초기화 (로그아웃)
    return redirect("/")



#목표설정 페이지로
@app.route('/goal',methods = ["GET"])
def goal():
    # 마이페이지에서 목표설정으로 이동 GET
    return render_template("Goal.html")

@app.route('/set_goal',methods = ["POST"])
def set_goal():
    # 목표를 설정하고 디비에 업데이트 후 마이페이지로 이동해야함
    userid = session.get("userid")
    user_goal_time = request.form.get('weekly_goal')
    sec_user_goal_time = int(user_goal_time) * 3600
    db.users.update_one({'userid': userid},{'$set' : {'goal_time' : sec_user_goal_time}})
    return redirect(url_for("mypage"))



#마이페이지로
@app.route('/mypage',methods = ["GET"])
def mypage():
    userid = session.get("userid")
    
    
    #현재시간
    now = datetime.now( )
    
    user = db.users.find_one({"userid": userid}) #db에서 아이디로 검색
    if not user: #디비에 아이디 없을 때(예외 상황)
        return redirect(url_for("login"))
    
    #사용자의 이름 받아오기
    user_name = user.get("username")
    
    enter_time = user.get("enter_time")
    
    
    #오늘 공부한 시간(today_seconds) = 현재시간(now)- 입실시간(enter_time)
    today_seconds = 0
    if enter_time and enter_time.date() == now.date():
        #초단위로 오늘 공부 시간
        today_seconds = int((now.replace(tzinfo=None) - enter_time).total_seconds()) 
    
     # 시/분/초 변환
    hours = today_seconds // 3600
    minutes = (today_seconds % 3600) // 60
    seconds = today_seconds % 60
    
    #주간 목표시간 계산(DB sec단위 -> hour단위로)
    goals = user.get("goal_time", 0 ) # 0의 의미 : 필드가 존재하지 않으면 0을 넣어라라 
    goal_hour = round(goals // 3600)
    
    #주간 목표시간 달성률(%) 계산
    study_time = user.get("study_time")
    if goals == 0:
        week_percent = 0
    else:
        week_percent = round(((study_time / goals)  * 100) ,2)
    
    #주간 공부시간 시/분 변환
    w_hours = round(study_time // 3600)
    w_minutes = round((study_time % 3600) // 60)
    #나의 순위(rank) 계산
    users = db.users.find().sort("study_time", -1)
    
    my_rank = -1
    for i, k in enumerate(users):
        if k["userid"] == userid:
            my_rank = i + 1
            break
    
    
    return render_template("Mypage.html",
                           username= user_name,
                           today_hours = hours,
                           today_minutes = minutes,
                           weekly_goal = goal_hour,
                           progress_percent = week_percent,
                           week_study_hour = w_hours,
                           week_study_minute = w_minutes,
                           rank = my_rank
                           )



if __name__ == '__main__':
   app.run('0.0.0.0', port=5000, debug=True)
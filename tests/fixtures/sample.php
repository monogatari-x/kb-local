<?php

class UserController {
    public function login($user) {
        return $user;
    }

    private function helper() {
        return null;
    }
}

function standalone() {
    return 42;
}
